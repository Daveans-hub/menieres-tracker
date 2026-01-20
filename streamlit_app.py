import streamlit as st
import google.generativeai as genai
import requests
from requests_oauthlib import OAuth2Session
import datetime
import pandas as pd

# --- CONFIG & SECRETS ---
st.set_page_config(page_title="Meniere's Tracker", layout="centered")
CLIENT_ID = st.secrets["FITBIT_CLIENT_ID"]
CLIENT_SECRET = st.secrets["FITBIT_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["FITBIT_REDIRECT_URI"]
SCOPE = ["activity", "heartrate", "location", "nutrition", "profile", "settings", "sleep", "oxygen_saturation", "temperature"]

st.title("👂 Meniere's Tracker")

# --- FITBIT LOGIN LOGIC ---
if 'fb_token' not in st.session_state:
    st.session_state.fb_token = None

# 1. Start the Login Process
fitbit = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)

# Check if we are returning from a Fitbit login
query_params = st.query_params
if "code" in query_params and not st.session_state.fb_token:
    auth_code = query_params["code"]
    token = fitbit.fetch_token(
        "https://api.fitbit.com/oauth2/token",
        code=auth_code,
        client_secret=CLIENT_SECRET,
        include_client_id=True
    )
    st.session_state.fb_token = token
    st.success("Successfully connected to Fitbit!")

# Show Login Button if not connected
if not st.session_state.fb_token:
    authorization_url, state = fitbit.authorization_url("https://www.fitbit.com/oauth2/authorize")
    st.link_button("🔗 Login with Fitbit", authorization_url, use_container_width=True)
    st.info("Please login to Fitbit to capture your health data.")
    st.stop() # Stops the rest of the app until login is done

# --- APP TABS (Only visible after login) ---
tab1, tab2, tab3 = st.tabs(["🚨 Emergency Log", "🍽️ Food AI", "📊 History"])

def get_fb_stats():
    token = st.session_state.fb_token['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    stats = {}
    
    try:
        # Sleep
        s = requests.get(f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json", headers=headers).json()
        stats["Sleep Score"] = s['summary']['totalMinutesAsleep']
        # Heart
        h = requests.get(f"https://api.fitbit.com/1/user/-/activities/heart/date/{today}/1d.json", headers=headers).json()
        stats["RHR"] = h['activities-heart'][0]['value']['restingHeartRate']
        # HRV
        hrv = requests.get(f"https://api.fitbit.com/1/user/-/hrv/date/{today}.json", headers=headers).json()
        stats["HRV"] = hrv['hrv'][0]['value']['dailyRmssd']
    except:
        return {"Error": "Token Expired. Please refresh."}
    return stats

with tab1:
    if st.button("🚨 LOG DIZZY SPELL NOW", use_container_width=True):
        stats = get_fb_stats()
        # Get Pressure
        res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={st.secrets['OPENWEATHER_KEY']}").json()
        pressure = res['main']['pressure']
        
        entry = {"Time": datetime.datetime.now().strftime("%H:%M"), "Pressure": pressure, **stats}
        st.write("Logged Data:", entry)
        st.success("Captured everything.")

with tab2:
    st.subheader("Food Scanner")
    # (AI Food code goes here - same as previous version)
