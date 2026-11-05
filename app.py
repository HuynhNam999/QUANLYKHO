import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    with open("service_account.json", "r", encoding="utf-8") as f:
        creds_info = json.load(f)
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scopes))
try:
    gc = init_connection()
    sh = gc.open_by_key("11iic-jKj_RX7iPLwPCIOjatIWqr5X2Or9H2HnbHIQ")
    worksheet = sh.worksheet("TonKho")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: {e}")
    st.stop()
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
if not st.session_state.logged_in:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ KHO")
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submit_btn = st.form_submit_button("Đăng nhập")
        if submit_btn:
            if username == "admin" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.rerun()
            elif username == "nhanvien" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()
st.sidebar.title(f"👤 Xin chào: {st.session_state.role}")
if st.sidebar.button("Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()
st.title("📦 QUẢN LÝ KHO LINH KIỆN & COMBO VĨNH VIỄN")
st.subheader("📊 Bảng Tồn Kho & Chi Tiết")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    st.markdown("---")
    st.subheader("🔍 Tra cứu chi tiết linh kiện / combo")
    selected_item = st.selectbox("Chọn mã linh kiện để xem ảnh & nhật ký", df.iloc[:, 0].tolist())
    if selected_item:
        item_row = df[df.iloc[:, 0] == selected_item].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Mã LK:** {item_row.get(df.columns[0], '')}")
            st.write(f"**Tên LK:** {item_row.get(df.columns
