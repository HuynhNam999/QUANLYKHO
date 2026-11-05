import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
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
    ["📊 Tổng quan tồn kho", "🔍 Tra cứu & Lọc chi tiết", "📥 Nhập mới / Cập nhật", "📤 Xuất kho thông minh"]
)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()
# --- GIAO DIỆN CHÍNH BÊN PHẢI ---
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
                st.markdown("### 📄 Thông tin chi tiết sản phẩm / Combo")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Mã LK:** {item_row.get('Ma_LK', '')}")
                    st.write(f"**Tên LK:** {item_row.get('Ten_LK', '')}")
                    st.write(f"**Số lượng tồn:** {item_row.get('So_luong', '')} {item_row.get('Don_vi', '')}")
                    # Hiển thị cấu thành linh kiện nếu là Combo
                    thanh_phan = item_row.get('Thanh_phan', None)
                    if thanh_phan and isinstance(thanh_phan, list) and len(thanh_phan) > 0:
                        st.markdown("**🔗 Các linh kiện thành phần trong bộ:**")
                        for tp in thanh_phan:
                            sub_m = tp.get('ma')
                            sub_sl = tp.get('sl')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            sub_name = sub_match.iloc[0]["Ten_LK"] if not sub_match.empty else ""
                            st.write(f"- `{sub_m}` ({sub_name}) | Số lượng dùng trong 1 bộ: **{sub_sl}**")
                with col_info2:
                    img_url = item_row.get('Hinh_anh', '')
                    if img_url and str(img_url).startswith("http"):
                        st.image(str(img_url), caption=f"Ảnh: {item_row.get('Ten_LK', '')}", width=250)
                    else:
                        st.info("Chưa có link hình ảnh.")
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
                st.info(f"Đang lọc ngày: **{format_ngay}** | Hạng mục: **{loai_loc}**")
            if not filtered_df.empty:
                st.dataframe(filtered_df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)
            else:
                st.warning("Không tìm thấy dữ liệu phù hợp.")
        else:
            st.info("Kho hiện đang trống.")
    elif menu_choice == "📥 Nhập mới / Cập nhật":
        st.title("📥 NHẬP MỚI HOẶC CẬP NHẬT THÔNG TIN")
        st.markdown("---")
        with st.expander("📌 Hướng dẫn tạo Combo và Linh kiện thành phần", expanded=True):
            st.markdown("""
            * **Linh kiện lẻ**: Nhập mã, tên và số lượng bình thường.
            * **Combo sản phẩm**: Khai báo danh sách linh kiện thành phần bên dưới để hệ thống quản lý định mức.
            """)
        with st.form("add_update_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ma_lk = st.text_input("Mã linh kiện / Combo (VD: CB-MVRS-01)")
                ten_lk = st.text_input("Tên linh kiện / Combo (VD: Bộ cánh quạt xe máy)")
                so_luong = st.number_input("Số lượng", min_value=0, step=1)
                don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Cái", "Túi", "Combo", "Cuộn", "Hộp"])
            with col2:
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")
                ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập kho lô hàng mới")
            st.markdown("### 🧩 Khai báo linh kiện thành phần (Dành riêng cho Combo sản phẩm)")
            # Tạo danh sách hiển thị dạng: "[Mã] - Tên linh kiện" cho dễ kiểm soát
            options_list = ["Không chọn"]
            code_map = {}
            if not df.empty:
                for _, row in df.iterrows():
                    display_str = f"[{row['Ma_LK']}] - {row['Ten_LK']}"
                    options_list.append(display_str)
                    code_map[display_str] = row['Ma_LK']
            sub_col1, sub_col2, sub_col3 = st.columns(3)
            with sub_col1:
                tp1_opt = st.selectbox("Thành phần 1", options_list, key="tp1_o")
                tp1_sl = st.number_input("Số lượng dùng trong 1 bộ", min_value=1, value=1, key="tp1_s")
            with sub_col2:
                tp2_opt = st.selectbox("Thành phần 2", options_list, key="tp2_o")
                tp2_sl = st.number_input("Số lượng dùng trong 1 bộ ", min_value=1, value=1, key="tp2_s")
            with sub_col3:
                tp3_opt = st.selectbox("Thành phần 3", options_list, key="tp3_o")
                tp3_sl = st.number_input("Số lượng dùng trong 1 bộ  ", min_value=1, value=1, key="tp3_s")
            save_btn = st.form_submit_button("Lưu dữ liệu vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        danh_sach_thanh_phan = []
                        if tp1_opt != "Không chọn":
                            danh_sach_thanh_phan.append({"ma": code_map[tp1_opt], "sl": int(tp1_sl)})
                        if tp2_opt != "Không chọn":
                            danh_sach_thanh_phan.append({"ma": code_map[tp2_opt], "sl": int(tp2_
