import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd

st.set_page_config(page_title="Meniere's Helper", layout="centered")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("🔑 API Keys")
gemini_key = st.sidebar.text_input("Google AI Key", type="password")
fb_token = st.sidebar.text_input("Fitbit Access Token", type="password")

if gemini_key:
    genai.configure(api_key=gemini_key)

st.title("👂 Meniere's Tracker")

# Temporary data storage (We will connect Google Sheets in the next step!)
if 'data_log' not in st.session_state:
    st.session_state.data_log = []

tab1, tab2, tab3 = st.tabs(["🚨 Emergency Log", "🍽️ Food Scanner", "📊 History"])

# --- TAB 1: DIZZY LOG & FITBIT ---
with tab1:
    st.header("Log Dizzy Spell")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚨 LOG SPELL NOW", use_container_width=True):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Fetch Fitbit data automatically if token is there
            fb_data = {"Sleep": "N/A", "HRV": "N/A", "RHR": "N/A", "SpO2": "N/A", "Temp": "N/A"}
            if fb_token:
                headers = {"Authorization": f"Bearer {fb_token}"}
                try:
                    # Fetch Sleep
                    slp = requests.get("https://api.fitbit.com/1.2/user/-/sleep/date/today.json", headers=headers).json()
                    fb_data["Sleep"] = slp['summary']['totalMinutesAsleep']
                    # Fetch Heart (RHR)
                    hrt = requests.get("https://api.fitbit.com/1/user/-/activities/heart/date/today/1d.json", headers=headers).json()
                    fb_data["RHR"] = hrt['activities-heart'][0]['value']['restingHeartRate']
                except:
                    st.warning("Fitbit token expired or invalid.")

            entry = {"Date": now, "Type": "Dizzy Spell", **fb_data}
            st.session_state.data_log.append(entry)
            st.success(f"Logged! Fitbit stats captured.")

# --- TAB 2: FOOD AI ---
with tab2:
    st.header("AI Food Analyzer")
    uploaded_file = st.file_uploader("Snap a photo", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and gemini_key:
        if st.button("Analyze Meal"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([
                "Estimate Sodium (mg), Caffeine (mg), and Water (oz). Return a simple list.",
                {"mime_type": "image/jpeg", "data": uploaded_file.getvalue()}
            ])
            st.info(response.text)
            st.session_state.data_log.append({
                "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
                "Type": "Meal", 
                "Details": response.text
            })

# --- TAB 3: HISTORY ---
with tab3:
    st.header("Log History")
    if st.session_state.data_log:
        st.dataframe(pd.DataFrame(st.session_state.data_log))
    else:
        st.write("No entries yet.")
