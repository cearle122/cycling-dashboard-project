"""
ONE-TIME SETUP SCRIPT
This was used to initially authorize the Strava app and download activity data.
You don't need to run this again unless re-authorizing.
"""

import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
auth_code = '812fd4b952819bc197ec910e815a08dc3ce889e0'

response = requests.post(
    url='https://www.strava.com/oauth/token',
    data={
        'client_id': os.getenv('STRAVA_CLIENT_ID'),
        'client_secret': os.getenv('STRAVA_CLIENT_SECRET'),
        'code': auth_code,
        'grant_type': 'authorization_code'
    } 
)

token_data = response.json()
access_token = token_data['access_token']
print("Access Token:", access_token)

# Save refresh token
if 'refresh_token' in token_data:
    with open('strava_refresh_token.txt', 'w') as f:
        f.write(token_data['refresh_token'])
    print("Refresh token saved!")

# fetch activities
headers = {'Authorization': f'Bearer {access_token}'}

# all activities
all_activities = []
page = 1

while True:
    print(f"Fetching page {page}...")
    response = requests.get(
        'https://www.strava.com/api/v3/athlete/activities',
        headers=headers,
        params={
            'per_page': 200,
            'page': page
        }
    )
    activities = response.json()

    if not activities:
        break

    all_activities.extend(activities)
    page += 1

# saves activities to CSV
df = pd.json_normalize(all_activities)
df.to_csv('my_strava_activities.csv', index=False)
print(f"Saved {len(all_activities)} activities to my_strava_activities.csv")