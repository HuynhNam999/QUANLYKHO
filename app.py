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
            # Hiển thị thêm cột Thành phần nếu có
            display_cols = ["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]
            df_display = df[display_cols]
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
                            st.write(- f"Mã: `{tp.get('ma')}` | Số lượng cần cho 1 bộ: **{tp.get('sl')}**")
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
            * Nếu bạn tạo **Linh kiện lẻ**: Chỉ cần điền mã, tên, số lượng bình thường.
            * Nếu bạn tạo **Combo (VD: Bộ cánh quạt `CB-MVRS-01`)**: Bạn có thể khai báo danh sách các mã linh kiện con cấu thành nên bộ này ở phía dưới để hệ thống tự động trừ kho linh kiện con khi xuất bộ lớn!
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
            st.markdown("### 🧩 Khai báo linh kiện thành phần (Chỉ dùng nếu đây là Combo sản phẩm)")
            all_codes = df["Ma_LK"].tolist() if not df.empty else []
            # Cho phép cấu hình tối đa 3 thành phần trong combo (có thể mở rộng thêm tùy ý)
            sub_col1, sub_col2, sub_col3 = st.columns(3)
            with sub_col1:
                tp1_ma = st.selectbox("Thành phần 1 - Mã LK", ["Không chọn"] + all_codes, key="tp1_m")
                tp1_sl = st.number_input("Số lượng dùng trong 1 bộ", min_value=1, value=1, key="tp1_s")
            with sub_col2:
                tp2_ma = st.selectbox("Thành phần 2 - Mã LK", ["Không chọn"] + all_codes, key="tp2_m")
                tp2_sl = st.number_input("Số lượng dùng trong 1 bộ ", min_value=1, value=1, key="tp2_s")
            with sub_col3:
                tp3_ma = st.selectbox("Thành phần 3 - Mã LK", ["Không chọn"] + all_codes, key="tp3_m")
                tp3_sl = st.number_input("Số lượng dùng trong 1 bộ  ", min_value=1, value=1, key="tp3_s")
            save_btn = st.form_submit_button("Lưu dữ liệu vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        # Gom nhóm danh sách thành phần
                        danh_sach_thanh_phan = []
                        if tp1_ma != "Không chọn":
                            danh_sach_thanh_phan.append({"ma": tp1_ma, "sl": int(tp1_sl)})
                        if tp2_ma != "Không chọn":
                            danh_sach_thanh_phan.append({"ma": tp2_ma, "sl": int(tp2_sl)})
                        if tp3_ma != "Không chọn":
                            danh_sach_thanh_phan.append({"ma": tp3_ma, "sl": int(tp3_sl)})
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
                            "Hinh_anh": hinh_anh,
                            "Thanh_phan": danh_sach_thanh_phan
                        }
                        supabase.table("Ton_kho").upsert(new_data).execute()
                        st.success("Đã lưu cấu hình và dữ liệu thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên!")
    elif menu_choice == "📤 Xuất kho thông minh":
        st.title("📤 XUẤT KHO THÔNG MINH (Tự động trừ linh kiện thành phần)")
        st.markdown("---")
        if not df.empty:
            selected_export_item = st.selectbox("1️⃣ Chọn mã sản phẩm / Combo cần xuất", df["Ma_LK"].tolist())
            current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
            hien_thi_ten = current_item_row["Ten_LK"]
            ton_hien_tai = current_item_row["So_luong"]
            don_vi_tinh = current_item_row["Don_vi"]
            hinh_anh_cu = current_item_row["Hinh_anh"]
            thanh_phan_list = current_item_row.get("Thanh_phan", [])
            st.info(f"📌 **Tên sản phẩm:** {hien_thi_ten} | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}**")
            # Hiển thị cảnh báo nếu đây là Combo có chứa các linh kiện con
            if thanh_phan_list and isinstance(thanh_phan_list, list) and len(thanh_phan_list) > 0:
                st.warning("⚠️ **Combo này bao gồm các linh kiện thành phần sau sẽ bị trừ tự động theo số lượng xuất:**")
                for tp in thanh_phan_list:
                    sub_item = df[df["Ma_LK"] == tp.get('ma')]
                    sub_name = sub_item.iloc[0]["Ten_LK"] if not sub_item.empty else "Không rõ"
                    sub_stock = sub_item.iloc[0]["So_luong"] if not sub_item.empty else 0
                    st.write(f"- Mã linh kiện con: **{tp.get('ma')}** ({sub_name}) | Cần trừ: **{tp.get('sl')} x Số lượng xuất** | Tồn kho hiện tại của con: `{sub_stock}`")
            with st.form("export_form", clear_on_submit=True):
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    so_luong_xuat = st.number_input("Số lượng xuất kho", min_value=1, step=1, value=1)
                with col_ex2:
                    ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                noi_dung_xuat = st.text_input("Nội dung / Mục đích xuất kho", placeholder="Ví dụ: Xuất lắp ráp bộ cánh quạt")
                export_btn = st.form_submit_button("Xác nhận Xuất Kho Thông Minh")
                if export_btn:
                    try:
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                        # 1. Trừ kho chính của Combo
                        so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                        nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất kho: {so_luong_xuat} {don_vi_tinh}"
                        if noi_dung_xuat:
                            nhat_ky_xuat += f" | Nội dung: {noi_dung_xuat}"
                        # Cập nhật lại Combo chính
                        update_data = {
                            "Ma_LK": selected_export_item,
                            "Ten_LK": hien_thi_ten,
                            "So_luong": so_luong_moi,
                            "Don_vi": don_vi_tinh,
                            "Nhat_ky": nhat_ky_xuat,
                            "Hinh_anh": hinh_anh_cu,
                            "Thanh_phan": thanh_phan_list
                        }
                        supabase.table("Ton_kho").upsert(update_data).execute()
                        # 2. Tự động trừ kho các linh kiện thành phần bên trong nếu có
                        if thanh_phan_list and isinstance(thanh_phan_list, list):
                            for tp in thanh_phan_list:
                                sub_ma = tp.get('ma')
                                sub_sl_can_dung = int(tp.get('sl')) * int(so_luong_xuat)
                                # Lấy thông tin hiện tại của linh kiện con trong kho
                                sub_row_df = df[df["Ma_LK"] == sub_ma]
                                if not sub_row_df.empty:
                                    sub_row = sub_row_df.iloc[0]
                                    sub_ton_cu = int(sub_row["So_luong"])
                                    sub_ton_moi = sub_ton_cu - sub_sl_can_dung
                                    # Ghi log cho linh kiện con
                                    sub_logs = sub_row.get("Nhat_ky", "")
                                    sub_log_moi = f"\n[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📉 Trừ tự động theo Combo '{selected_export_item}': -{sub_sl_can_dung}"
                                    supabase.table("Ton_kho").update({
                                        "So_luong": sub_ton_moi,
                                        "Nhat_ky": sub_logs + sub_log_moi
                                    }).eq("Ma_LK", sub_ma).execute()
                        st.success(f"Xuất kho thành công! Hệ thống đã tự động trừ kho Combo và các linh kiện thành phần.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi thực hiện xuất kho: {e}")
        else:
            st.warning("Kho hiện đang trống!")
