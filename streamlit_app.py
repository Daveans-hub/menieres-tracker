import streamlit as st
import google.generativeai as genai
import requests
import base64
import datetime
import pandas as pd

# --- APP CONFIG & SECRETS ---
st.set_page_config(page_title="Meniere's Tracker", layout="centered")

# Get secrets from Streamlit Vault
try:
    CLIENT_ID = st.secrets["FITBIT_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FITBIT_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FITBIT_REDIRECT_URI"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    st.error("Missing Secrets in Streamlit Settings!")
    st.stop()

st.title("👂 Meniere's Tracker")

# --- OAUTH HELPERS ---
if 'fb_token' not in st.session_state:
    st.session_state.fb_token = None

# This encodes your ID and Secret for Fitbit
auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

# --- LOGIN LOGIC ---
# 1. Check if we just returned from Fitbit with a 'code'
if "code" in st.query_params and st.session_state.fb_token is None:
    code = st.query_params["code"]
    
    # Exchange code for token
    token_url = "https://api.fitbit.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID
    }
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    res = requests.post(token_url, data=data, headers=headers).json()
    
    if "access_token" in res:
        st.session_state.fb_token = res
        st.query_params.clear() # Clear the URL so it doesn't error on refresh
        st.rerun()
    else:
        st.error(f"Login failed: {res.get('errors')}")

# 2. If not logged in, show the button
if not st.session_state.fb_token:
    scope = "activity heartrate nutrition profile sleep oxygen_saturation temperature"
    login_url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scope}"
    st.link_button("🔗 Step 1: Login with Fitbit", login_url, use_container_width=True)
    st.info("Click the button above to authorize the app.")
    st.stop()

# --- THE APP (Only shows after login) ---
st.success("✅ Fitbit Connected")

tab1, tab2, tab3 = st.tabs(["🚨 Log Spell", "🍽️ Food AI", "📊 History"])

def fetch_fitbit():
    token = st.session_state.fb_token['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    data = {}
    try:
        # Sleep
        s = requests.get(f"https://api.fitbit.com/1.2/user/-/sleep/date/{date}.json", headers=headers).json()
        data["Sleep_Min"] = s['summary']['totalMinutesAsleep']
        # Heart
        h = requests.get(f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/1d.json", headers=headers).json()
        data["RHR"] = h['activities-heart'][0]['value']['restingHeartRate']
    except:
        data["Note"] = "Could not pull data (check if you wore watch last night)"
    return data

with tab1:
    if st.button("🚨 LOG DIZZY SPELL NOW", use_container_width=True):
        fb_stats = fetch_fitbit()
        # Get Pressure
        w_url = f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={WEATHER_KEY}"
        pressure = requests.get(w_url).json()['main']['pressure']
        
        entry = {
            "Time": datetime.datetime.now().strftime("%H:%M"),
            "Pressure": pressure,
            **fb_stats
        }
        st.write("Captured Stats:", entry)
        st.balloons()

with tab2:
    st.subheader("Food & Water AI")
    uploaded_file = st.file_uploader("Snap meal photo", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        if st.button("Analyze with AI"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([
                "Return ONLY a JSON list: Sodium(mg), Caffeine(mg), Water(oz), Sweeteners(type).",
                {"mime_type": "image/jpeg", "data": uploaded_file.getvalue()}
            ])
            st.info(response.text)
