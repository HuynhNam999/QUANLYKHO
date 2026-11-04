import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    b64_str = st.secrets["GOOGLE_CREDENTIALS_B64"]
    creds_info = json.loads(base64.b64decode(b64_str).decode("utf-8"))
    return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
try:
    gc = init_connection()
    worksheet = gc.open("QuanLyKho").worksheet("TonKho")
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()
