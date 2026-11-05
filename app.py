import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
# Khởi tạo kết nối Supabase an toàn tuyệt đối từ Secrets
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase: Client = init_supabase()
# Tải dữ liệu từ bảng Ton_kho
@st.cache_data(ttl=0)
def load_data():
    try:
        response = supabase.table("Ton_kho").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Quản lý đăng nhập hệ thống
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
if not st.session_state.logged_in:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ KHO")
    with st.form("login_form"):
        username_input = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submit_btn = st.form_submit_button("Đăng nhập")
        if submit_btn:
            if username_input == "admin" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.session_state.username = "Quản trị viên (Admin)"
                st.rerun()
            elif username_input == "nhanvien" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.session_state.username = "Nhân viên kho"
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()
st.sidebar.title(f"👤 Xin chào: {st.session_state.role}")
if st.sidebar.button("Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()
st.title("📦 QUẢN LÝ KHO LINH KIỆN & COMBO VĨNH VIỄN")
st.subheader("📊 Bảng Tồn Kho & Chi Tiết")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    st.markdown("---")    
    # --- BỔ SUNG KHU VỰC LỌC HẠNG MỤC ---
    st.subheader("🔍 Tra cứu chi tiết & Lọc theo hạng mục")   
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        # Bộ lọc phân loại hạng mục hoạt động
        loai_loc = st.selectbox(
            "Lọc xem theo danh mục nhật ký", 
            ["Tất cả", "📥 Nhập kho", "📤 Xuất kho", "🔄 Cập nhật thông tin"]
        )
    with col_filter2:
        # Lọc danh sách theo mã linh kiện
        selected_item = st.selectbox("Chọn mã linh kiện để xem chi tiết ảnh", df["Ma_LK"].tolist())
    # Xử lý hiển thị thông tin chi tiết dựa trên mã được chọn
    if selected_item:
        item_row = df[df["Ma_LK"] == selected_item].iloc[0]   
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Mã LK:** {item_row.get('Ma_LK', '')}")
            st.write(f"**Tên LK:** {item_row.get('Ten_LK', '')}")
            st.write(f"**Số lượng tồn:** {item_row.get('So_luong', '')} {item_row.get('Don_vi', '')}")      
            nhat_ky_goc = str(item_row.get('Nhat_ky', 'Chưa có nhật ký'))
            st.write(f"**Nhật ký thao tác gần nhất:** {nhat_ky_goc}")          
        with col2:
            img_url = item_row.get('Hinh_anh', '')
            if img_url and str(img_url).startswith("http"):
                st.image(str(img_url), caption=f"Ảnh: {item_row.get('Ten_LK', '')}", width=250)
            else:
                st.info("Chưa có link hình ảnh cho linh kiện/combo này.")
    # Hiển thị bảng nhật ký tổng hợp theo bộ lọc hạng mục đã chọn
    st.markdown("### 📋 Lịch sử hoạt động toàn kho theo hạng mục")
    if loai_loc != "Tất cả":
        # Lọc các dòng trong DataFrame có chứa từ khóa loại thao tác tương ứng
        keyword_map = {
            "📥 Nhập kho": "Nhập kho",
            "📤 Xuất kho": "Xuất kho",
            "🔄 Cập nhật thông tin": "Cập nhật"
        }
        kw = keyword_map.get(loai_loc, "")
        filtered_df = df[df["Nhat_ky"].str.contains(kw, na=False)]
        st.info(f"Đang hiển thị các mục thuộc hạng mục: **{loai_loc}** (Tổng số: {len(filtered_df)} bản ghi)")
        if not filtered_df.empty:
            st.dataframe(filtered_df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)
        else:
            st.warning(f"Chưa có dữ liệu nào thuộc hạng mục '{loai_loc}'.")
    else:
        st.dataframe(df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)

else:
    st.info("Kho hiện đang trống. Hãy thêm linh kiện mới bên dưới!")
st.markdown("---")
st.subheader("➕ Thêm / Cập Nhật Linh Kiện & Combo Mới")

# Hướng dẫn quy tắc đặt mã
with st.expander("📌 Hướng dẫn quy tắc đặt Mã Linh Kiện / Combo (Bấm vào để xem)", expanded=False):
    st.markdown("""
    * **Linh kiện lẻ:** `LK-[Nhóm]-[TênViếtTắt]-[SốThứTự]` (Ví dụ: `LK-IC-NE555-01`)
    * **Combo sản phẩm:** `CB-[TênGói]-[PhiênBản]` (Ví dụ: `CB-ARDUINO-V1`)
    """)
with st.form("add_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        ma_lk = st.text_input("Mã linh kiện / Combo (VD: LK-IC-01)")
        ten_lk = st.text_input("Tên linh kiện / Combo")
        so_luong = st.number_input("Số lượng", min_value=0, step=1)
        don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Cái", "Túi", "Combo", "Cuộn", "Hộp", "Chiếc"])
    with col2:
        loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho", "📤 Xuất kho", "🔄 Cập nhật thông tin"])
        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
        ghi_chu_tay = st.text_input("Ghi chú thêm (tùy chọn)", placeholder="Ví dụ: Kiểm kê định kỳ tháng này")
        hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")  
    save_btn = st.form_submit_button("Lưu dữ liệu vào Database")
    if save_btn:
        if ma_lk and ten_lk:
            try:
                nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                nhat_ky_str = f"[{ngay_hien_tai}] 👤 {Nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
                if ghi_chu_tay:
                    nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                new_data = {
                    "Ma_LK": ma_lk,
                    "Ten_LK": ten_lk,
                    "So_luong": int(so_luong),
                    "Don_vi": don_vi,
                    "Nhat_ky": nhat_ky_str,
                    "Hinh_anh": hinh_anh
                }               
                supabase.table("Ton_kho").upsert(new_data).execute()
                st.success("Đã ghi nhận lịch sử và lưu dữ liệu thành công vĩnh viễn!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi khi lưu dữ liệu: {e}")
        else:
            st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện!")
