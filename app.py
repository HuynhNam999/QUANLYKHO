import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=scopes))
try:
    gc = init_connection()
    worksheet = gc.open("QuanLyKho").worksheet("TonKho")
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
        if st.form_submit_button("Đăng nhập"):
            if username == "admin" and password == "123456":
                st.session_state.logged_in, st.session_state.role = True, "Admin"
                st.rerun()
            elif username == "nhanvien" and password == "123456":
                st.session_state.logged_in, st.session_state.role = True, "Nhân viên"
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()
st.sidebar.title(f"👤 Xin chào: {st.session_state.role}")
if st.sidebar.button("Đăng xuất"):
    st.session_state.logged_in, st.session_state.role = False, None
    st.rerun()
st.title("📦 QUẢN LÝ KHO LINH KIỆN & COMBO VĨNH VIỄN")
df = pd.DataFrame(worksheet.get_all_records())
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
            st.write(f"**Tên LK:** {item_row.get(df.columns[1], '')}")
            st.write(f"**Số lượng tồn:** {item_row.get(df.columns[2], '')} {item_row.get(df.columns[3], '')}")
            st.write(f"**Nhật ký xuất nhập:** {item_row.get('NhatKyXuatNhap', 'Chưa có nhật ký')}")
        with col2:
            img_url = item_row.get('HinhAnh', '')
            if img_url and str(img_url).startswith("http"):
                st.image(str(img_url), caption=f"Ảnh: {item_row.get(df.columns[1], '')}", width=250)
            else:
                st.info("Chưa có link hình ảnh cho linh kiện/combo này.")
else:
    st.info("Kho hiện đang trống. Hãy thêm linh kiện mới bên dưới!")
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
    if st.form_submit_button("Lưu dữ liệu vào Google Sheets"):
        if ma_lk and ten_lk:
            worksheet.append_row([ma_lk, ten_lk, so_luong, don_vi, nhat_ky, hinh_anh])
            st.success("Đã lưu dữ liệu thành công lên Google Sheets vĩnh viễn!")
            st.rerun()
        else:
            st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện!")
