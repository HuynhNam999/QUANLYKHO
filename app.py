import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- KẾT NỐI GOOGLE SHEETS TRỰC TIẾP TỪ FILE JSON TRÊN GITHUB ---
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file("service_account.json", scopes=scopes)
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
            st.write(f"**Nhat ky xuat nhap:** {item_row.get('NhatKyXuatNhap', 'Chua co nhat ky')}")
            
        with col_info2:
            img_url = item_row.get('HinhAnh', '')
            if img_url and str(img_url).startswith("http"):
                st.image(str(img_url), caption=f"Ảnh: {item_row.get(df.columns[1], '')}", width=250)
            else:
                st.info("Chưa có link hình ảnh cho linh kiện/combo này.")
else:
    st.info("Kho hiện đang trống. Hãy thêm linh kiện mới bên dưới!")

# Form nhập liệu
st.markdown("---")
st.subheader("➕ Thêm / Cập Nhật Linh Kiện & Combo Mới")
with st.form("add_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        ma_lk = st.text_input("Mã linh kiện / Combo")
        ten_lk = st.text_input("Tên linh kiện / Combo")
        so_luong = st.number_input("Số lượng", min_value=0, step=1)
    with col2:
        don_vi = st.text_input("Đơn vị tính (Cái, Bộ, Combo...)")
        nhat_ky = st.text_input("Nhật ký xuất nhập")
        hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")
    
    submitted = st.form_submit_button("Lưu dữ liệu vào Google Sheets")
    if submitted:
        if ma_lk and ten_lk:
            worksheet.append_row([ma_lk, ten_lk, so_luong, don_vi, nhat_ky, hinh_anh])
            st.success("Đã lưu dữ liệu thành công lên Google Sheets vĩnh viễn!")
            st.rerun()
        else:
            st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện!")
