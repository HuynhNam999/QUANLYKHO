import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Đọc trực tiếp file service_account.json có sẵn trong kho GitHub
    with open("service_account.json", "r", encoding="utf-8") as f:
        creds_info = json.load(f)
    return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
try:
    gc = init_connection()
    worksheet = gc.open("QuanLyKho").worksheet("TonKho")
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()
