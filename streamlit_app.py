import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd
import base64
from streamlit_gsheets import GSheetsConnection

# --- APP CONFIG & KEYS ---
st.set_page_config(page_title="Meniere's Helper", layout="centered")

try:
    API_KEY = st.secrets["GEMINI_KEY"]
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    GSHEET_ID = st.secrets["GSHEET_ID"]
    CLIENT_ID = st.secrets["FITBIT_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FITBIT_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FITBIT_REDIRECT_URI"]
    
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Setup Error: Check your Streamlit Secrets names!")
    st.stop()

# Connect to your Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("👂 Meniere's Tracker")

# --- FITBIT LOGIN ---
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
        st.rerun()

if not st.session_state.fb_token:
    scope = "activity%20heartrate%20nutrition%20sleep%20temperature%20oxygen_saturation"
    login_url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scope}"
    st.link_button("🔗 CONNECT FITBIT TO START", login_url, use_container_width=True)
    st.stop()

# --- HELPERS: DATA FETCH ---
def get_all_stats():
    token = st.session_state.fb_token['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    stats = {"Date": today, "Pressure": "N/A", "Sleep": 0, "HRV": 0, "RHR": 0, "SpO2": 0, "Temp": 0, "Steps": 0}
    
    try:
        # Weather
        w_url = f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={WEATHER_KEY}"
        stats["Pressure"] = requests.get(w_url).json()['main']['pressure']
        # Fitbit (Sleep & Heart)
        slp = requests.get(f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json", headers=headers).json()
        stats["Sleep"] = slp['summary']['totalMinutesAsleep']
        hrt = requests.get(f"https://api.fitbit.com/1/user/-/activities/heart/date/{today}/1d.json", headers=headers).json()
        stats["RHR"] = hrt['activities-heart'][0]['value']['restingHeartRate']
    except: pass
    return stats

# --- MOBILE TABS ---
tab1, tab2, tab3 = st.tabs(["🚨 LOG SPELL", "📸 FOOD SCAN", "🤖 AI ASSISTANT"])

with tab1:
    st.subheader("Emergency Vertigo Log")
    if st.button("🚨 LOG DIZZY SPELL NOW", type="primary", use_container_width=True):
        with st.spinner("Capturing medical stats..."):
            stats = get_all_stats()
            # CREATE THE ROW FOR YOUR SHEET
            new_row = pd.DataFrame([{
                "ID": str(datetime.datetime.now().timestamp())[:8],
                "Date": stats["Date"],
                "Photo": "Vertigo Event",
                "Sodium": 0, "Caffeine": 0, "Water": 0,
                "Barometric Pressure": stats["Pressure"],
                "Sleep score": stats["Sleep"],
                "RHR": stats["RHR"]
            }])
            # SAVE TO GOOGLE SHEET
            conn.create(spreadsheet=f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}", data=new_row)
            st.success("Spell Logged to Spreadsheet!")
            st.balloons()

with tab2:
    st.subheader("Rear Camera Food Scan")
    img_file = st.file_uploader("Snap meal photo", type=["jpg", "png", "jpeg"])
    if img_file:
        if st.button("Analyze & Save"):
            with st.spinner("AI checking ingredients..."):
                response = model.generate_content(["Estimate Sodium(mg), Caffeine(mg), Water(oz). Return ONLY JSON: {'sodium': 0, 'caffeine': 0, 'water': 0}", {"mime_type": "image/jpeg", "data": img_file.getvalue()}])
                import json
                ai_data = json.loads(response.text.replace("'", '"'))
                stats = get_all_stats()
                
                food_row = pd.DataFrame([{
                    "ID": str(datetime.datetime.now().timestamp())[:8],
                    "Date": stats["Date"],
                    "Sodium": ai_data['sodium'],
                    "Caffeine": ai_data['caffeine'],
                    "Water": ai_data['water'],
                    "Barometric Pressure": stats["Pressure"]
                }])
                conn.create(spreadsheet=f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}", data=food_row)
                st.info(f"Saved: {ai_data['sodium']}mg Sodium")

with tab3:
    st.subheader("Meniere's Assistant")
    # This reads your sheet to look for trends
    df = conn.read(spreadsheet=f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}")
    user_query = st.chat_input("Ask about your triggers...")
    if user_query:
        history = df.tail(10).to_string()
        chat_res = model.generate_content(f"User data: {history}. Question: {user_query}")
        st.write(chat_res.text)
