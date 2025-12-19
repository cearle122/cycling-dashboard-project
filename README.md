# Strava Cycling Dashboard

A Streamlit dashboard for analyzing cycling data using the Strava API.
It shows ride summaries, route maps, training volume, and AI-generated training insights.

## Features
- Performance overview (distance, time, power)
- Individual ride analysis
- Interactive route maps
- Training metrics (IF, TSS, Normalized Power)
- Weekly training volume chart
- AI-powered training insights

## Requirements
- Python 
- Strava API access
- Groq API key (optional, for AI insights)

## Strava API

In order to get your personalized data, you will need to navigate to https://www.strava.com/dashboard on a desktop and log in.

From there, go to your profile in the top right corner and select 'Settings'.

Go to 'My API Application' at the bottom of the settings list.

Here, you will need to apply/create your own Strava API application. Once you have done that, you will have access to your client ID and secret, and your refresh token.

Then, to get the authorization code, enter this link into your browser:
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
but make sure to replace 'YOUR_CLIENT_ID' with your client ID from your Strava API application.

You will then be redirected to this link:
http://localhost/?state=&code=LONG_STRING_OF_CHARACTERS&scope=read,activity:read_all
Everything BETWEEN 'code=' and '&scope' is your authorization code. Save it, and paste it into the strava_api.py file to gather your Strava data into a CSV.

## Setup

1. Clone the repository

git clone https://github.com/yourusername/strava-cycling-dashboard.git  
cd strava-cycling-dashboard

2. Install dependencies

pip install -r requirements.txt

3. Create environment file

Copy the sample file:

cp sample.env .env

Edit `.env` and add your credentials:

STRAVA_CLIENT_ID=your_client_id  
STRAVA_CLIENT_SECRET=your_client_secret  
GROQ_API_KEY=your_groq_api_key

4. Add your Strava refresh token

Create a file named:

strava_refresh_token.txt

Paste your personal Strava refresh token into the file.

5. Add your activity data

Export your Strava activities and place the CSV file in the project root:

my_strava_activities.csv

6. Run the app

streamlit run dashboard.py

## Notes
- Make sure to adjust FTP in dashboard.py to your actual FTP for accurate results.
- Secrets and personal data are not committed to this repository.
- `.env`, refresh tokens, and real CSV files are excluded via `.gitignore`.
- This project is for personal analytics and learning purposes.
