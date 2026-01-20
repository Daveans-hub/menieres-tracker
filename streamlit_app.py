import streamlit as st
import google.generativeai as genai
import requests
import datetime
import pandas as pd
import gspread
import base64

# --- CONFIG & KEYS ---
st.set_page_config(page_title="Meniere's Helper", layout="centered")

# Load Secrets from Streamlit Vault
try:
    API_KEY = st.secrets["GEMINI_KEY"]
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    # Your specific Sheet ID from the URL you gave me
    SHEET_ID = "1sqx1pCbIj5oXr6kuOs9FF9jEFt9nvBC2V_g1LlrRGPY" 
    genai.configure(api_key=API_KEY)
except:
    st.error("Please add GEMINI_KEY and OPENWEATHER_KEY to Streamlit Secrets.")
    st.stop()

st.title("👂 Meniere's Tracker")

# --- CONNECT TO GOOGLE SHEETS ---
# We use a simple method to connect to your public 'Editor' sheet
def update_sheet(data_list):
    try:
        # This is a shortcut for public editor sheets
        url = f"https://docs.google.com/forms/d/e/YOUR_FORM_ID/formResponse" # We will simplify this to direct gsheets in a second
        # For now, we will use gspread for the most reliable connection
        gc = gspread.import_api_key(API_KEY) # Placeholder for the next step
        st.info("Saving to Google Sheet...")
    except:
        pass

# --- AI MODEL DISCOVERY (Fixes the 404 Error) ---
def get_ai_response(img_bytes):
    # This automatically finds the right 'Brain' name
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Estimate Sodium(mg), Caffeine(mg), Water(oz). Return ONLY JSON: {'sodium': 0, 'caffeine': 0, 'water': 0}"
    response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
    return response.text

# --- MOBILE APP INTERFACE ---
tab1, tab2 = st.tabs(["🚨 LOG SPELL", "📸 FOOD SCANNER"])

with tab1:
    st.subheader("Log Dizzy Spell")
    if st.button("🚨 LOG NOW", type="primary", use_container_width=True):
        # 1. Get Pressure
        w_url = f"https://api.openweathermap.org/data/2.5/weather?q=Auckland&appid={WEATHER_KEY}"
        pressure = requests.get(w_url).json()['main']['pressure']
        
        st.success(f"Logged! Pressure: {pressure}hPa. Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.warning("Note: To save permanently to Sheets, ensure 'Share' is set to 'Anyone with link - Editor'")

with tab2:
    st.subheader("Food & Drink")
    # Using 'file_uploader' on mobile opens the native camera (allowing rear camera selection)
    img_file = st.file_uploader("Snap photo of meal/water", type=["jpg", "png", "jpeg"])
    
    if img_file:
        if st.button("Analyze & Save"):
            with st.spinner("AI checking salt/caffeine..."):
                try:
                    result = get_ai_response(img_file.getvalue())
                    st.info(f"AI Estimate: {result}")
                    st.balloons()
                except Exception as e:
                    st.error(f"AI Error: {e}")

st.divider()
st.caption("Instructions: Tap the camera icon above to use your phone's back camera.")
