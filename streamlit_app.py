import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd
import base64
import uuid

# --- CONFIG & KEYS ---
st.set_page_config(page_title="Meniere's Pro Tracker", layout="centered")

try:
    genai.configure(api_key=st.secrets["GEMINI_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    GSHEET_ID = st.secrets["GSHEET_ID"]
    CLIENT_ID = st.secrets["FITBIT_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FITBIT_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FITBIT_REDIRECT_URI"]
except Exception as e:
    st.error("Missing Secrets in Streamlit Settings!")
    st.stop()

st.title("👂 Meniere's Tracker")

# --- FITBIT LOGIN LOGIC ---
if 'fb_token' not in st.session_state:
    st.session_state.fb_token = None

if "code" in st.query_params and st.session_state.fb_token is None:
    code = st.query_params["code"]
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    res = requests.post("https://api.fitbit.com/oauth2/token", 
                        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
                        headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}).json()
    if "access_token" in res:
        st.session_state.fb_token = res
        st.query_params.clear()
        st.rerun()

if not st.session_state.fb_token:
    scope = "activity%20heartrate%20nutrition%20sleep%20temperature%20oxygen_saturation"
    login_url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scope}"
    st.link_button("🔗 CONNECT FITBIT TO START", login_url, use_container_width=True)
    st.stop()

# --- HELPERS: FETCH DATA ---
def get_all_stats():
    token = st.session_state.fb_token['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    stats = {}
    
    # 1. Weather (Auckland)
    try:
        w_url = f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={WEATHER_KEY}"
        stats["Pressure"] = requests.get(w_url).json()['main']['pressure']
    except: stats["Pressure"] = "N/A"

    # 2. Fitbit Metrics
    try:
        # Sleep & Score
        slp = requests.get(f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json", headers=headers).json()
        stats["Sleep"] = slp['summary']['totalMinutesAsleep']
        # Heart (RHR & HRV)
        hrt = requests.get(f"https://api.fitbit.com/1/user/-/activities/heart/date/{today}/1d.json", headers=headers).json()
        stats["RHR"] = hrt['activities-heart'][0]['value']['restingHeartRate']
        # HRV
        hrv = requests.get(f"https://api.fitbit.com/1/user/-/hrv/date/{today}.json", headers=headers).json()
        stats["HRV"] = hrv['hrv'][0]['value']['dailyRmssd']
        # SpO2
        spo2 = requests.get(f"https://api.fitbit.com/1/user/-/spo2/date/{today}.json", headers=headers).json()
        stats["SpO2"] = spo2[0]['value']['avg']
        # Activity
        act = requests.get(f"https://api.fitbit.com/1/user/-/activities/date/{today}.json", headers=headers).json()
        stats["Activity"] = act['summary']['steps']
    except:
        pass
    return stats

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🚨 LOG SPELL", "📸 FOOD SCAN", "🤖 AI TRENDS"])

with tab1:
    if st.button("🚨 LOG DIZZY SPELL NOW", type="primary", use_container_width=True):
        with st.spinner("Fetching Fitbit & Weather..."):
            data = get_all_stats()
            # This is where we will add the code to write to Google Sheets in the next step
            st.success("Spell Logged Locally!")
            st.write(data)

with tab2:
    st.subheader("Rear Camera Food Scan")
    img_file = st.file_uploader("Snap photo", type=["jpg", "png", "jpeg"])
    if img_file:
        if st.button("Analyze & Save to Sheet"):
            with st.spinner("AI analyzing ingredients..."):
                prompt = "Return ONLY JSON: {'sodium': 0, 'caffeine': 0, 'water': 0, 'sweeteners': 'none'}"
                response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_file.getvalue()}])
                st.info(response.text)

with tab3:
    st.subheader("Meniere's AI Assistant")
    st.write("I analyze your history to find trends.")
    
    # Read the Google Sheet to look for trends
    sheet_url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/export?format=csv"
    try:
        df = pd.read_csv(sheet_url)
        user_query = st.chat_input("E.g., What caused my spell on Tuesday?")
        if user_query:
            context = df.tail(15).to_string()
            chat_res = model.generate_content(f"Data: {context}. Question: {user_query}")
            with st.chat_message("assistant"):
                st.write(chat_res.text)
    except:
        st.warning("Please ensure your Google Sheet is shared as 'Anyone with link - Editor'")
