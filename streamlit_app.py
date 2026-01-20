import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Meniere's Helper", layout="centered")

# --- SETUP API KEYS (We will hide these later) ---
# For now, we will put them in the sidebar for testing
st.sidebar.header("Settings")
gemini_key = st.sidebar.text_input("Google AI Key", type="password")
weather_key = st.sidebar.text_input("OpenWeather Key (Optional)", type="password")

if gemini_key:
    genai.configure(api_key=gemini_key)

st.title("👂 Meniere's Tracker")

# --- DATABASE (Simulated for now) ---
if 'data_log' not in st.session_state:
    st.session_state.data_log = []

# --- TAB 1: LOG DIZZY SPELL ---
tab1, tab2, tab3 = st.tabs(["Dizzy Log", "Food Scanner", "History"])

with tab1:
    st.header("Emergency Log")
    if st.button("🚨 LOG DIZZY SPELL NOW", use_container_width=True):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Get Weather info automatically
        pressure = "1013" # Default if no key
        if weather_key:
            try:
                res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={weather_key}").json()
                pressure = res['main']['pressure']
            except:
                pass
        
        entry = {"Date": now, "Type": "Dizzy Spell", "Pressure": pressure, "Details": "Vertigo Triggered"}
        st.session_state.data_log.append(entry)
        st.success(f"Logged at {now}. Barometric Pressure: {pressure} hPa")

# --- TAB 2: FOOD SCANNER ---
with tab2:
    st.header("Food & Drink AI")
    uploaded_file = st.file_uploader("Take a photo of your meal/water", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and gemini_key:
        st.image(uploaded_file, caption="Processing...", width=300)
        
        if st.button("Analyze with AI"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Convert image to bytes for AI
            img_bytes = uploaded_file.getvalue()
            
            response = model.generate_content([
                "Estimate Sodium (mg), Caffeine (mg), and Water (oz) in this photo. Return a simple list.",
                {"mime_type": "image/jpeg", "data": img_bytes}
            ])
            
            st.info(response.text)
            
            # Save to history
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.data_log.append({"Date": now, "Type": "Food Log", "Details": response.text})

# --- TAB 3: HISTORY ---
with tab3:
    st.header("Recent Logs")
    if st.session_state.data_log:
        df = pd.DataFrame(st.session_state.data_log)
        st.table(df)
    else:
        st.write("No logs yet today.")
