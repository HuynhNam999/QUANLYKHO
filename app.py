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
    [
        "📊 Tổng quan tồn kho", 
        "🔍 Tra cứu & Lọc chi tiết", 
        "📥 Nhập mới Combo", 
        "📥 Nhập mới Linh kiện lẻ", 
        "📤 Xuất kho Combo", 
        "📤 Xuất kho Linh kiện lẻ"
    ]
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
    # 1. TỔNG QUAN TỒN KHO
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
    # 2. TRA CỨU & LỌC CHI TIẾT
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
                    st.write(f"**Mã LK/VT/CB:** {item_row.get('Ma_LK', '')}")
                    st.write(f"**Tên:** {item_row.get('Ten_LK', '')}")
                    st.write(f"**Số lượng tồn:** {item_row.get('So_luong', '')} {item_row.get('Don_vi', '')}")
                    thanh_phan = item_row.get('Thanh_phan', None)
                    if thanh_phan and isinstance(thanh_phan, list) and len(thanh_phan) > 0:
                        st.markdown("**🔗 Các linh kiện/vật tư thành phần trong bộ:**")
                        for tp in thanh_phan:
                            sub_m = tp.get('ma')
                            sub_sl = tp.get('sl')
                            sub_img = tp.get('img', '')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            sub_name = sub_match.iloc[0]["Ten_LK"] if not sub_match.empty else ""
                            st.write(f"- `{sub_m}` ({sub_name}) | Định mức: **{sub_sl}**")
                            if sub_img:
                                st.image(sub_img, width=80)
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
    # 3. NHẬP MỚI COMBO (Giao diện Phần 2 dạng dọc gọn gàng có cột ảnh)
    elif menu_choice == "📥 Nhập mới Combo":
        st.title("📦 KHAI BÁO & NHẬP MỚI / CHỈNH SỬA COMBO SẢN PHẨM")
        st.markdown("---")
        che_do_nhap = st.radio(
            "⚙️ Chọn phương thức khai báo Combo:",
            ["➕ Nhập mới hoàn toàn", "🔄 Lấy theo dữ liệu Combo cũ để chỉnh sửa (thêm/bớt thành phần)"],
            horizontal=True
        )
        combo_options = ["-- Chọn Combo cũ --"]
        combo_dict = {}
        if not df.empty:
            c_df = df[df["Ma_LK"].str.startswith("CB", na=False)]
            for _, r in c_df.iterrows():
                d_str = f"{r['Ma_LK']} - {r['Ten_LK']}"
                combo_options.append(d_str)
                combo_dict[d_str] = r
        selected_cb = None
        if che_do_nhap.startswith("🔄"):
            selected_cb = st.selectbox("📂 Chọn mã Combo cũ cần tải dữ liệu:", combo_options)
        def_ma = ""
        def_ten = ""
        def_sl = 0
        def_dv = "Bộ"
        def_img = ""
        def_tp = []
        if selected_cb and selected_cb != "-- Chọn Combo cũ --":
            row_cb = combo_dict[selected_cb]
            def_ma = row_cb["Ma_LK"]
            def_ten = row_cb["Ten_LK"]
            def_sl = int(row_cb["So_luong"]) if "So_luong" in row_cb else 0
            def_dv = row_cb["Don_vi"] if row_cb["Don_vi"] in ["Bộ", "Hộp", "Combo"] else "Bộ"
            def_img = row_cb["Hinh_anh"] if row_cb["Hinh_anh"] else ""
            def_tp = row_cb.get("Thanh_phan", [])
        with st.form("add_combo_form", clear_on_submit=True):
            st.markdown("### 🏷️ PHẦN 1: THÔNG TIN COMBO")
            c1, c2 = st.columns(2)
            with c1:
                ma_lk = st.text_input("Mã Combo (VD: CB-MVRS-01)", value=def_ma)
                ten_lk = st.text_input("Tên Combo (VD: Bộ cánh quạt xe máy)", value=def_ten)
                so_luong = st.number_input("Số lượng bộ", min_value=0, step=1, value=def_sl)
            with c2:
                don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Hộp", "Combo"], index=["Bộ", "Hộp", "Combo"].index(def_dv) if def_dv in ["Bộ", "Hộp", "Combo"] else 0)
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)", value=def_img)
            ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Cập nhật thêm/bớt linh kiện thành phần combo")
            st.markdown("---")
            st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN TRONG COMBO (Hiển thị theo chiều dọc, hỗ trợ tối đa 10 linh kiện)")
            st.info("💡 Mỗi dòng gồm: Mã linh kiện/vật tư, Định mức số lượng và Link hình ảnh thành phần.")
            def get_tp_val(idx, field):
                if idx < len(def_tp):
                    return def_tp[idx].get(field, "")
                return ""
            tps_input = []
            # Hiển thị 10 dòng theo chiều dọc rõ ràng
            for i in range(1, 11):
                st.markdown(f"**Thành phần {i}**")
                col_m, col_s, col_i = st.columns([2, 1, 2])
                with col_m:
                    m_val = st.text_input(f"Mã LK/VT {i}", value=get_tp_val(i-1, 'ma'), key=f"tp{i}_m")
                with col_s:
                    s_val = st.number_input(f"Định mức {i}", min_value=1, value=int(get_tp_val(i-1, 'sl')) if get_tp_val(i-1, 'sl') else 1, key=f"tp{i}_s")
                with col_i:
                    i_val = st.text_input(f"Link ảnh LK {i} (URL)", value=get_tp_val(i-1, 'img'), key=f"tp{i}_i")
                st.markdown("---")
                tps_input.append((m_val, s_val, i_val))
            danh_sach_thanh_phan = []
            for ma_con, sl, img_con in tps_input:
                if ma_con and ma_con.strip() != "":
                    danh_sach_thanh_phan.append({
                        "ma": ma_con.strip(), 
                        "sl": int(sl),
                        "img": img_con.strip() if img_con else ""
                    })
            save_btn = st.form_submit_button("💾 Lưu Cấu Hình Combo vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
                        if ghi_chu_tay:
                            nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                        if not df.empty and ma_lk in df["Ma_LK"].values:
                            old_row = df[df["Ma_LK"] == ma_lk].iloc[0]
                            old_logs = old_row.get("Nhat_ky", "")
                            if old_logs:
                                nhat_ky_str = old_logs + "\n" + nhat_ky_str
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
                        st.success("Đã lưu thành công dữ liệu Combo vào Database!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên Combo!")
    # 4. NHẬP MỚI LINH KIỆN LẺ
    elif menu_choice == "📥 Nhập mới Linh kiện lẻ":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        st.info("💡 Bạn có thể **chọn mã có sẵn từ danh sách** để hệ thống tự điền tên và cập nhật, hoặc **gõ mã mới** để khai báo vật tư lẻ mới.")
        existing_items = ["-- Tạo mới / Nhập mới hoàn toàn --"]
        item_dict = {}
        if not df.empty:
            for _, r in df.iterrows():
                display_str = f"{r['Ma_LK']} - {r['Ten_LK']}"
                existing_items.append(display_str)
                item_dict[display_str] = r
        selected_existing = st.selectbox("🔍 Chọn mã linh kiện/vật tư có sẵn (hoặc chọn 'Tạo mới')", existing_items)
        def_ma = ""
        def_ten = ""
        def_dv = "Cái"
        def_img = ""
        if selected_existing != "-- Tạo mới / Nhập mới hoàn toàn --":
            matched_row = item_dict[selected_existing]
            def_ma = matched_row["Ma_LK"]
            def_ten = matched_row["Ten_LK"]
            def_dv = matched_row["Don_vi"] if matched_row["Don_vi"] in ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"] else "Cái"
            def_img = matched_row["Hinh_anh"] if matched_row["Hinh_anh"] else ""
        with st.form("add_item_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ma_lk = st.text_input("Mã LK / VT (VD: LK-CANHQUAT-01)", value=def_ma)
                ten_lk = st.text_input("Tên linh kiện / vật tư", value=def_ten)
                so_luong = st.number_input("Số lượng nhập thêm / tồn kho", min_value=0, step=1)
            with c2:
                don_vi = st.selectbox("Đơn vị tính", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"], index=["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"].index(def_dv) if def
