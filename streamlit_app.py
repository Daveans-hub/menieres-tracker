import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd
import base64

# --- APP CONFIG ---
st.set_page_config(page_title="Meniere's Helper", layout="centered")

# Load Secrets
CLIENT_ID = st.secrets["FITBIT_CLIENT_ID"]
CLIENT_SECRET = st.secrets["FITBIT_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["FITBIT_REDIRECT_URI"]
WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
genai.configure(api_key=st.secrets["GEMINI_KEY"])

st.title("👂 Meniere's Tracker")

# --- SESSION STATE ---
if 'fb_token' not in st.session_state:
    st.session_state.fb_token = None
if 'history' not in st.session_state:
    st.session_state.history = []

# --- LOGIN LOGIC ---
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
    login_url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=activity%20heartrate%20nutrition%20sleep%20temperature"
    st.link_button("🔗 STEP 1: CONNECT FITBIT", login_url, use_container_width=True)
    st.stop()

# --- THE MOBILE APP TABS ---
tab1, tab2, tab3 = st.tabs(["🚨 LOG", "📸 FOOD", "🤖 ASK AI"])

with tab1:
    st.subheader("Quick Log")
    if st.button("🚨 LOG DIZZY SPELL NOW", type="primary", use_container_width=True):
        # Fetch Data
        w_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={WEATHER_KEY}").json()
        pressure = w_res['main']['pressure']
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        entry = {"Date": now, "Type": "Dizzy Spell", "Pressure": pressure}
        st.session_state.history.append(entry)
        st.success(f"Logged! Pressure: {pressure}hPa")

with tab2:
    st.subheader("Food Scanner")
    # Camera Input is perfect for mobile
    img_file = st.camera_input("Take a photo of your meal")
    
    if img_file:
        if st.button("Analyze Meal"):
            with st.spinner("AI is checking ingredients..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([
                    "Estimate Sodium(mg), Caffeine(mg), Water(oz), and Sweeteners. Format: Sodium: X, Caffeine: Y, Water: Z",
                    {"mime_type": "image/jpeg", "data": img_file.getvalue()}
                ])
                st.info(response.text)
                st.session_state.history.append({"Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "Type": "Meal", "Details": response.text})

with tab3:
    st.subheader("Meniere's Assistant")
    user_query = st.chat_input("Ask about your triggers...")
    if user_query:
        # Feed the AI her recent history for context
        context = str(st.session_state.history[-5:]) # Last 5 events
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat_response = model.generate_content(f"The user has Meniere's. Recent history: {context}. Question: {user_query}")
        with st.chat_message("assistant"):
            st.write(chat_response.text)
