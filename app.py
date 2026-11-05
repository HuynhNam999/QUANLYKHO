import streamlit as st
import pandas as pd
from supabase import create_client, Client
# Khởi tạo kết nối Supabase an toàn tuyệt đối từ Secrets
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase: Client = init_supabase()
# Tải dữ liệu từ bảng ton_kho
@st.cache_data(ttl=0)
def load_data():
    try:
        response = supabase.table("ton_kho").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Quản lý đăng nhập hệ thống
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
    selected_item = st.selectbox("Chọn mã linh kiện để xem ảnh & nhật ký", df["ma_lk"].tolist())
    if selected_item:
        item_row = df[df["ma_lk"] == selected_item].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Mã LK:** {item_row.get('ma_lk', '')}")
            st.write(f"**Tên LK:** {item_row.get('ten_lk', '')}")
            st.write(f"**Số lượng tồn:** {item_row.get('so_luong', '')} {item_row.get('don_vi', '')}")
            st.write(f"**Nhật ký xuất nhập:** {item_row.get('nhat_ky', 'Chưa có nhật ký')}")
        with col2:
            img_url = item_row.get('hinh_anh', '')
            if img_url and str(img_url).startswith("http"):
                st.image(str(img_url), caption=f"Ảnh: {item_row.get('ten_lk', '')}", width=250)
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
    save_btn = st.form_submit_button("Lưu dữ liệu vào Database")
    if save_btn:
        if ma_lk and ten_lk:
            try:
                new_data = {
                    "ma_lk": ma_lk,
                    "ten_lk": ten_lk,
                    "so_luong": int(so_luong),
                    "don_vi": don_vi,
                    "nhat_ky": nhat_ky,
                    "hinh_anh": hinh_anh
                }
                supabase.table("ton_kho").insert(new_data).execute()
                st.success("Đã lưu dữ liệu thành công lên hệ thống vĩnh viễn!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu dữ liệu: {e}")
        else:
            st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện!")
