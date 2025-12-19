# Personal cycling dashboard project using Strava API

# SET YOUR FTP HERE 
FTP = 225

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import polyline
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv
from groq import Groq

# page config
st.set_page_config(
    page_title="Strava Cycling Dashboard",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# cache the csv data
@st.cache_data
def load_data():
    """Load and cache the CSV data"""
    return pd.read_csv('my_strava_activities.csv')

# Strava API and Groqcredentials
load_dotenv()
client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')
groq_api_key = os.getenv('GROQ_API_KEY')

if not client_id or not client_secret:
       st.error("Missing Strava credentials. Please check your .env file.")
       st.stop()

groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
REFRESH_TOKEN_FILE = 'strava_refresh_token.txt'

# try to get refresh token from txt file
if os.path.exists(REFRESH_TOKEN_FILE):
    with open(REFRESH_TOKEN_FILE, 'r') as f:
        refresh_token = f.read().strip()
else:
    st.error("Refresh token file not found. Please run the setup script first.")
    st.stop()


# get access token from refresh token
def get_access_from_refresh(refresh_token, client_id, client_secret):
    response = requests.post(
        'https://www.strava.com/oauth/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
    )
    tokens = response.json()
    if 'access_token' not in tokens:
        st.error(f"Failed to get access token from Strava: {tokens}")
        st.stop()
    if tokens['refresh_token'] != refresh_token:
        with open(REFRESH_TOKEN_FILE, 'w') as f:
            f.write(tokens['refresh_token'])
    return tokens['access_token'], tokens['refresh_token']

ACCESS_TOKEN, refresh_token = get_access_from_refresh(refresh_token, client_id, client_secret)

# function to refresh the access token, not to be confused with the actual refresh token
def refresh_access_token(refresh_token, client_id, client_secret):
    response = requests.post(
        'https://www.strava.com/oauth/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        }
    )
    if response.status_code == 200:
        return response.json()
    else:
        st.error('Failed to refresh access token.')
        return None

# function to mainly get map details for an activity, still using CSV for individual ride statistics
@st.cache_data(ttl=3600)
def get_activity_details(activity_id, access_token, refresh_token=None, client_id=None, client_secret=None):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=false"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json(), access_token, refresh_token
    elif response.status_code == 401 and refresh_token and client_id and client_secret:
        tokens = refresh_access_token(refresh_token, client_id, client_secret)
        if tokens:
            new_access_token = tokens['access_token']
            new_refresh_token = tokens['refresh_token']
            headers = {'Authorization': f'Bearer {new_access_token}'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json(), new_access_token, new_refresh_token
        st.error(f"Error loading activity data after refresh (HTTP {response.status_code})")
        return None, access_token, refresh_token
    else:
        st.error(f"Error loading activity data (HTTP {response.status_code})")
        return None, access_token, refresh_token

# constants for conversions
METERS_TO_FEET = 3.28084
METERS_TO_MILES = 0.000621371
MPS_TO_MPH = 2.23694

def get_np(ridename):
    return ridename['weighted_average_watts']

def get_if(ridename):
    np = get_np(ridename)
    return np / FTP

def get_tss(ridename):
    np = get_np(ridename)
    intensity_factor = get_if(ridename)
    time = ridename['moving_time']
    return (time * np * intensity_factor) / (FTP * 3600) * 100

def convert_meters_to_feet(meters):
    return meters * METERS_TO_FEET

def convert_meters_to_miles(meters):
    return meters * METERS_TO_MILES

def get_ai_insights(ride_data, weekly_data, ftp):
    if not groq_client:
        return None
    
    prompt = f"""You are a cycling coach analyzing training data. Provide brief, actionable insights (3-4 sentences max).

Rider's FTP: {ftp}W

Recent Training Summary:
- Total rides in dataset: {len(ride_data)}
- Average power: {ride_data['average_watts'].mean():.0f}W
- Total distance: {ride_data['distance'].sum() / 1609:.0f} miles
- Recent weekly hours: {weekly_data.tail(4)['moving_time_hours'].mean():.1f} hrs/week

Latest Ride:
- Distance: {ride_data.iloc[-1]['distance'] / 1609:.1f} miles
- Average Power: {ride_data.iloc[-1]['average_watts']:.0f}W
- Duration: {ride_data.iloc[-1]['moving_time'] / 60:.0f} minutes

Provide:
1. One key strength you notice
2. One area for improvement
3. One specific training recommendation

Keep it concise and motivating."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Unable to generate insights: {str(e)}"

# CSS for styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    h1 {
        color: #FC4C02;
        font-weight: 700;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

##########################
# dashboard overview
##########################
df = load_data()

# header
st.title("🚴 Cycling Dashboard")
st.markdown("Track your training, analyze your performance, and visualize your progress.")
st.markdown("---")

st.header("Performance Overview")

# calculate totals
total_rides = len(df)
total_distance = df['distance'].sum() / 1000  # km
total_elevation_gain = df['total_elevation_gain'].sum()  # m
total_power = df['average_watts'].mean()  # average watts
total_moving_time = df['moving_time'].sum() / 3600  # hours

# display in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Rides", f"{total_rides:,}")
    
with col2:
    st.metric(
        "Total Distance", 
        f"{total_distance:.0f} km",
        delta=f"{convert_meters_to_miles(total_distance * 1000):.0f} mi"
    )
    
with col3:
    st.metric("Total Time", f"{total_moving_time:.1f} hrs")
    
with col4:
    st.metric("Avg Power", f"{total_power:.0f} W", delta=f"FTP: {FTP}W")

st.markdown("---")

#########################
# highest average power ride
#########################
st.header("Highest Average Power Ride")

df_power = df.dropna(subset=['average_watts'])
if len(df_power) > 0:
    max_power_ride = df_power.loc[df_power['average_watts'].idxmax()]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### {max_power_ride['name']}")
        st.markdown(f"**Date:** {pd.to_datetime(max_power_ride['start_date_local']).strftime('%B %d, %Y')}")
        
    with col2:
        st.metric("Average Power", f"{max_power_ride['average_watts']:.0f} W", delta="Personal Best")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Distance", f"{convert_meters_to_miles(max_power_ride['distance']):.2f} mi")
    with col2:
        st.metric("Duration", f"{max_power_ride['moving_time'] / 60:.0f} min")
    with col3:
        st.metric("Elevation", f"{convert_meters_to_feet(max_power_ride['total_elevation_gain']):.0f} ft")
else:
    st.info("No power data available in your activities.")

st.markdown("---")

############################
# view specific ride data
############################
st.header("Ride Details")

df['ride_label'] = df['name'] + " - " + pd.to_datetime(df['start_date_local']).dt.strftime('%Y-%m-%d')
selected_label = st.selectbox("Select a ride to analyze:", df['ride_label'], label_visibility="collapsed")
selected_ride = df[df['ride_label'] == selected_label].iloc[0]

# ride header
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"{selected_ride['name']}")
    st.caption(f"Completed on {pd.to_datetime(selected_ride['start_date_local']).strftime('%B %d, %Y at %I:%M %p')}")

# main stats in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Distance", f"{convert_meters_to_miles(selected_ride['distance']):.2f} mi")
with col2:
    st.metric("Duration", f"{selected_ride['moving_time'] / 60:.0f} min")
with col3:
    st.metric("Avg Speed", f"{selected_ride['average_speed'] * MPS_TO_MPH:.1f} mph")
with col4:
    st.metric("Elevation", f"{convert_meters_to_feet(selected_ride['total_elevation_gain']):.0f} ft")

# power metrics (if available)
if pd.notnull(selected_ride['average_watts']):
    st.markdown("#### Power Analysis")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Average Power", f"{selected_ride['average_watts']:.0f} W")
    with col2:
        st.metric("Normalized Power", f"{get_np(selected_ride):.0f} W")
    with col3:
        st.metric("Intensity Factor", f"{get_if(selected_ride):.2f}")
    with col4:
        tss = get_tss(selected_ride)
        tss_label = "Easy" if tss < 60 else "Moderate" if tss < 100 else "Hard"
        st.metric("TSS", f"{tss:.0f}", delta=tss_label)
else:
    st.info("No power data available for this ride.")

###################
# ride map
###################
st.markdown("#### 🗺️ Route Map")

activity_details, ACCESS_TOKEN, refresh_token = get_activity_details(
    selected_ride['id'], ACCESS_TOKEN, refresh_token, client_id, client_secret
)

if activity_details and activity_details.get('map', {}).get('summary_polyline'):
    coords = polyline.decode(activity_details['map']['summary_polyline'])
    m = folium.Map(location=coords[0], zoom_start=13, tiles='OpenStreetMap')
    folium.PolyLine(coords, color="#FC4C02", weight=3, opacity=0.8).add_to(m)
    
    # start/end markers
    folium.Marker(
        coords[0], 
        popup="Start",
        icon=folium.Icon(color='green', icon='play')
    ).add_to(m)
    folium.Marker(
        coords[-1], 
        popup="Finish",
        icon=folium.Icon(color='red', icon='stop')
    ).add_to(m)
    
    st_folium(m, width=None, height=500)
else:
    st.info("No route data available for this ride.")

######################
# AI insights Section
######################
if groq_client and len(df_power) > 0:
    st.header("Groq Training Insights")
    with st.spinner("Analyzing your training data..."):

        df_temp = df.copy()
        df_temp['week'] = pd.to_datetime(df_temp['start_date_local']).dt.to_period('W').apply(lambda x: x.start_time)
        df_temp['moving_time_hours'] = df_temp['moving_time'] / 3600
        weekly_data = df_temp.groupby('week')['moving_time_hours'].sum().reset_index()
        
        insights = get_ai_insights(df_power, weekly_data, FTP)
        
        if insights:
            st.info(insights)
        else:
            st.info("Unable to generate insights at this time.")
            
    st.markdown("---")

######################
# graph showing total riding hours per week
######################
st.header("Training Volume")

df['week'] = pd.to_datetime(df['start_date_local']).dt.to_period('W').apply(lambda x: x.start_time)
df['moving_time_hours'] = df['moving_time'] / 3600

weekly_hours = df.groupby('week')['moving_time_hours'].sum().reset_index()
weekly_hours = weekly_hours.tail(12) # last 12 weeks

fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(weekly_hours['week'], weekly_hours['moving_time_hours'], color='#FC4C02', alpha=0.7)
ax.set_title('Weekly Training Hours (Last 12 Weeks)', fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel('Week Starting', fontsize=12)
ax.set_ylabel('Hours', fontsize=12)
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax.tick_params(axis='x', rotation=45)
fig.tight_layout()

st.pyplot(fig)

# Footer
st.markdown("---")
st.caption("Data sourced from Strava API • Dashboard built with Streamlit • AI insights provided by Groq")