import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
# Cấu hình giao diện chiếm toàn màn hình
st.set_page_config(page_title="Quản Lý Kho Cá Nhân", page_icon="📦", layout="wide")
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
# --- MENU ĐIỀU HƯỚNG BÊN TRÁI ---
st.sidebar.title(f"👤 Xin chào: {st.session_state.role}")
st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Danh Mục Quản Lý")
menu_choice = st.sidebar.radio(
    "Chọn chức năng:",
    ["📊 Tổng quan tồn kho", "🔍 Tra cứu & Lọc chi tiết", "📥 Nhập mới / Cập nhật", "📤 Xuất kho"]
)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()
# --- GIAO DIỆN CHÍNH BÊN PHẢI (CĂN GIỮA) ---
_, main_col, _ = st.columns([0.05, 0.9, 0.05])
with main_col:
    if menu_choice == "📊 Tổng quan tồn kho":
        st.title("📦 TỒN KHO HỆ THỐNG")
        st.markdown("---")
        if not df.empty:
            def highlight_negative(val):
                color = 'red' if isinstance(val, (int, float)) and val < 0 else 'black'
                return f'color: {color}; text-align: center;'
            df_display = df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]]
            styled_df = df_display.style.map(
                lambda x: 'text-align: center;', subset=['Ma_LK', 'So_luong', 'Don_vi']
            ).map(
                highlight_negative, subset=['So_luong']
            )
            st.dataframe(styled_df, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm linh kiện mới ở mục bên trái!")
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU & LỌC CHI TIẾT SẢN PHẨM")
        st.markdown("---")
        if not df.empty:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                loai_loc = st.selectbox(
                    "Lọc theo danh mục hoạt động", 
                    ["Tất cả", "📥 Nhập kho", "📤 Xuất kho", "🔄 Cập nhật thông tin"]
                )
            with col_f2:
                selected_item = st.selectbox("Chọn mã linh kiện", df["Ma_LK"].tolist())
            with col_f3:
                bat_tat_ngay = st.checkbox("Lọc theo ngày cụ thể")
                ngay_chon = st.date_input("Chọn ngày", value=date.today())
            if selected_item:
                item_row = df[df["Ma_LK"] == selected_item].iloc[0]
                st.markdown("### 📄 Thông tin chi tiết sản phẩm")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Mã LK:** {item_row.get('Ma_LK', '')}")
                    st.write(f"**Tên LK:** {item_row.get('Ten_LK', '')}")
                    st.write(f"**Số lượng tồn:** {item_row.get('So_luong', '')} {item_row.get('Don_vi', '')}")
                    st.write(f"**Nhật ký thao tác:** {item_row.get('Nhat_ky', 'Chưa có nhật ký')}")
                with col_info2:
                    img_url = item_row.get('Hinh_anh', '')
                    if img_url and str(img_url).startswith("http"):
                        st.image(str(img_url), caption=f"Ảnh: {item_row.get('Ten_LK', '')}", width=250)
                    else:
                        st.info("Chưa có link hình ảnh cho linh kiện/combo này.")
            st.markdown("### 📋 NHẬT KÝ KHO")
            filtered_df = df.copy()
            if loai_loc != "Tất cả":
                keyword_map = {
                    "📥 Nhập kho": "Nhập kho",
                    "📤 Xuất kho": "Xuất kho",
                    "🔄 Cập nhật thông tin": "Cập nhật"
                }
                kw = keyword_map.get(loai_loc, "")
                filtered_df = filtered_df[filtered_df["Nhat_ky"].str.contains(kw, na=False)]
            if bat_tat_ngay:
                format_ngay = ngay_chon.strftime("%d/%m/%Y")
                filtered_df = filtered_df[filtered_df["Nhat_ky"].str.contains(format_ngay, na=False)]
                st.info(f"Đang lọc dữ liệu ngày: **{format_ngay}** | Hạng mục: **{loai_loc}** (Tổng số: {len(filtered_df)} bản ghi)")
            else:
                st.info(f"Đang hiển thị toàn bộ dữ liệu | Hạng mục: **{loai_loc}** (Tổng số: {len(filtered_df)} bản ghi)")
            if not filtered_df.empty:
                st.dataframe(filtered_df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)
            else:
                st.warning("Không tìm thấy dữ liệu phù hợp với bộ lọc.")
        else:
            st.info("Kho hiện đang trống.")
    elif menu_choice == "📥 Nhập mới / Cập nhật":
        st.title("📥 NHẬP MỚI HOẶC CẬP NHẬT THÔNG TIN")
        st.markdown("---")
        with st.expander("📌 Hướng dẫn quy tắc đặt Mã Linh Kiện / Combo (Bấm vào để xem)", expanded=False):
            st.markdown("""
            * **Linh kiện lẻ:** `LK-[Nhóm]-[TênViếtTắt]-[SốThứTự]` (Ví dụ: `LK-IC-NE555-01`)
            * **Combo sản phẩm:** `CB-[TênGói]-[PhiênBản]` (Ví dụ: `CB-ARDUINO-V1`)
            """)
        with st.form("add_update_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ma_lk = st.text_input("Mã linh kiện / Combo (VD: LK-IC-01)")
                ten_lk = st.text_input("Tên linh kiện / Combo")
                so_luong = st.number_input("Số lượng", min_value=0, step=1)
                don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Cái", "Túi", "Combo", "Cuộn", "Hộp", "Chiếc"])
            with col2:
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                ghi_chu_tay = st.text_input("Ghi chú thêm (tùy chọn)", placeholder="Ví dụ: Nhập hàng nhà cung cấp A")
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")
            save_btn = st.form_submit_button("Lưu dữ liệu vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
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
                        st.success("Đã lưu dữ liệu thành công vĩnh viễn!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện!")
    elif menu_choice == "📤 Xuất kho":
        st.title("📤 XUẤT KHO SẢN PHẨM")
        st.markdown("---")
        if not df.empty:
            # Dòng 1: Chọn mã linh kiện cần xuất (Bên ngoài form để tương tác trực tiếp cập nhật dòng 2)
            selected_export_item = st.selectbox("1️⃣ Chọn mã linh kiện cần xuất", df["Ma_LK"].tolist())
            # Lấy thông tin tương ứng với mã vừa chọn ở dòng 1
            current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
            hien_thi_ten = current_item_row["Ten_LK"]
            ton_hien_tai = current_item_row["So_luong"]
            don_vi_tinh = current_item_row["Don_vi"]
            hinh_anh_cu = current_item_row["Hinh_anh"]
            # Dòng 2: Tên linh kiện và số lượng tồn kho hiện tại
            st.info(f"📌 **2️⃣ Tên linh kiện:** {hien_thi_ten} (Đang tồn kho: **{ton_hien_tai} {don_vi_tinh}**)")
            # Form điền thông tin xuất kho
            with st.form("export_form", clear_on_submit=True):
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    so_luong_xuat = st.number_input("Số lượng xuất kho", min_value=1, step=1, value=1)
                with col_ex2:
                    ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                noi_dung_xuat = st.text_input("Nội dung / Mục đích xuất kho", placeholder="Ví dụ: Xuất lắp đặt công trình B")
                export_btn = st.form_submit_button("Xác nhận Xuất Kho")
                if export_btn:
                    try:
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                        # Tính toán lại số lượng tồn kho mới sau khi xuất
                        so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                        # Tạo chuỗi nhật ký xuất kho
                        nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất kho: {so_luong_xuat} {don_vi_tinh}"
                        if noi_dung_xuat:
                            nhat_ky_xuat += f" | Nội dung: {noi_dung_xuat}"
                        update_data = {
                            "Ma_LK": selected_export_item,
                            "Ten_LK": hien_thi_ten,
                            "So_luong": so_luong_moi,
                            "Don_vi": don_vi_tinh,
                            "Nhat_ky": nhat_ky_xuat,
                            "Hinh_anh": hinh_anh_cu
                        }
                        supabase.table("Ton_kho").upsert(update_data).execute()
                        st.success(f"Xuất kho thành công! Số lượng tồn kho mới của '{hien_thi_ten}' còn lại: {so_luong_moi} {don_vi_tinh}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xuất kho: {e}")
        else:
            st.warning("Kho hiện đang trống, chưa có mã nào để xuất!")
