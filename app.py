import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- KẾT NỐI GOOGLE SHEETS TỪ SECRETS AN TOÀN TUỆT ĐỐI ---
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Lấy thông tin từ st.secrets và chuyển đổi sang dạng dict an toàn
    sec = st.secrets["gcp_service_account"]
    
    creds_dict = dict(sec)
    # Xử lý triệt để lỗi định dạng private_key xuống dòng
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

try:
    gc = init_connection()
    sh = gc.open("QuanLyKho")
    worksheet = sh.worksheet("TonKho")
except Exception as e:
    st.error(f"Lỗi kết nối Google Sheets: Hãy kiểm tra lại tên file 'QuanLyKho' hoặc quyền Share email Bot! Chi tiết: {e}")
    st.stop()

# --- HỆ THỐNG ĐĂNG NHẬP PHÂN QUYỀN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ KHO")
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submit = st.form_submit_button("Đăng nhập")
        
        if submit:
            if username == "admin" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.success("Đăng nhập thành công với quyền Admin!")
                st.rerun()
            elif username == "nhanvien" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.success("Đăng nhập thành công với quyền Nhân viên!")
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()

# --- GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP ---
st.sidebar.title(f"👤 Xin chào: {st.session_state.role}")
if st.sidebar.button("Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

st.title("📦 QUẢN LÝ KHO LINH KIỆN & COMBO VĨNH VIỄN")

# Đọc dữ liệu từ Google Sheets
data = worksheet.get_all_records()
df = pd.DataFrame(data)

st.subheader("📊 Bảng Tồn Kho & Chi Tiết")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🔍 Tra cứu chi tiết linh kiện / combo")
    selected_item = st.selectbox("Chọn mã linh kiện để xem ảnh & nhật ký", df.iloc[:, 0].tolist() if len(df.columns) > 0 else [])
    
    if selected_item:
        item_row = df[df.iloc[:, 0] == selected_item].iloc[0]
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.write(f"**Mã LK:** {item_row.get(df.columns[0], '')}")
            st.write(f"**Tên LK:** {item_row.get(df.columns[1], '')}")
            st.write(f"**Số lượng tồn:** {item_row.get(df.columns[2], '')} {item_row.get(df.columns[3], '')}")
            st.write(f"**📝 Nhật ký xuất nhập:** {item_row.get('NhatKyXuatNhap', 'Chưa có nhật ký')}")
            
        with col_info2:
            img_url = item_row.get('HinhAnh', '')
            if img_url and str(img_url).startswith("http"):
