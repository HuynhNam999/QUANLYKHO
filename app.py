import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
import io
import re
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
# Hàm thông minh tự động sinh mã chuẩn CB, LK, VT
def generate_code_from_name(full_name, is_combo=False, item_type="VT"):
    if not full_name:
        return ""
    name_clean = full_name.strip()
    upper_name = name_clean.upper()
    if is_combo:
        name_code = "".join([c for c in upper_name if c.isalnum()])[:6]
        return f"CB-{name_code}" if name_code else "CB-01"
    prefix = item_type if item_type in ["LK", "VT"] else "VT"
    size_match = re.search(r'M\d+(?:[xX]\d+)?', upper_name)
    size_str = size_match.group(0).replace('X', 'x') if size_match else "GENERAL"
    grade_match = re.search(r'\b\d+\.\d+\b', upper_name)
    grade_str = f"_{grade_match.group(0)}" if grade_match else ""
    surface_code = ""
    if "NHÚNG NÓNG" in upper_name:
        surface_code = "_NN"
    elif "DACROMET" in upper_name:
        surface_code = "_DC"
    elif "MẠ" in upper_name:
        surface_code = "_MA"
    elif "NGẠNH" in upper_name:
        surface_code = "_NGANH"
    auto_code = f"{prefix}-{size_str}{grade_str}{surface_code}"
    auto_code = re.sub(r'[\s_]+', '_', auto_code).strip('_').upper()
    return auto_code
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
        "🔄 Xé lẻ Combo thành Linh kiện", 
        "📤 Xuất kho Combo", 
        "📤 Xuất kho Linh kiện lẻ",
        "📈 Báo cáo & Xuất Excel"
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
            df_filtered = df[df["So_luong"] >= 0].copy()
            def highlight_negative(val):
                color = 'red' if isinstance(val, (int, float)) and val < 0 else 'black'
                return f'color: {color}; text-align: center;'
            df_display = df_filtered[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]]
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
                            sub_name = tp.get('ten', '')
                            sub_sl = tp.get('sl')
                            sub_img = tp.get('img', '')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_name and not sub_match.empty:
                                sub_name = sub_match.iloc[0]["Ten_LK"]
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
    # 3. NHẬP MỚI COMBO
    elif menu_choice == "📥 Nhập mới Combo":
        st.title("📦 KHAI BÁO & NHẬP MỚI / CHỈNH SỬA COMBO SẢN PHẨM")
        st.markdown("---")
        che_do_nhap = st.radio(
            "⚙️ Chọn phương thức khai báo Combo:",
            ["➕ Nhập mới hoàn toàn", "🔄 Lấy theo dữ liệu Combo cũ để chỉnh sửa (thêm/bớt thành phần)"],
            horizontal=True
        )
        combo_dict = {}
        if not df.empty:
            c_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            for _, r in c_df.iterrows():
                d_str = f"{r['Ma_LK']} - {r['Ten_LK']}"
                combo_dict[d_str] = r.to_dict()
        if "edit_combo_data" not in st.session_state:
            st.session_state.edit_combo_data = None
        if che_do_nhap.startswith("🔄"):
            if combo_dict:
                col_sel1, col_sel2 = st.columns([3, 1])
                with col_sel1:
                    chosen_cb_str = st.selectbox("📂 Chọn mã Combo cũ cần tải dữ liệu:", list(combo_dict.keys()), key="select_combo_box")
                with col_sel2:
                    st.write("")
                    st.write("")
                    if st.button("🔄 Tải dữ liệu cũ"):
                        st.session_state.edit_combo_data = combo_dict[chosen_cb_str]
                        st.success(f"Đã tải dữ liệu của {chosen_cb_str}!")
                        st.rerun()
            else:
                st.warning("Chưa có mã Combo nào trong hệ thống!")
        else:
            if st.session_state.edit_combo_data is not None:
                st.session_state.edit_combo_data = None
        active_data = st.session_state.edit_combo_data
        def_ma = active_data.get("Ma_LK", "") if active_data else ""
        def_ten = active_data.get("Ten_LK", "") if active_data else ""
        def_dv = active_data.get("Don_vi", "Bộ") if active_data and active_data.get("Don_vi") in ["Bộ", "Hộp", "Combo"] else "Bộ"
        def_img = active_data.get("Hinh_anh", "") if active_data and active_data.get("Hinh_anh") else ""
        def_tp = active_data.get("Thanh_phan", []) if active_data else []
        st.markdown("### 🏷️ PHẦN 1: THÔNG TIN COMBO")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input("Tên Combo", value=def_ten, key="cb_ten_input", placeholder="VD: Bộ bàn ăn 4 ghế")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            cb_ma_mode = st.radio(
                "Phương thức mã Combo:",
                ["🤖 Hệ thống tự sinh mã", "✍️ Cá nhân tự viết mã"],
                horizontal=True,
                key="cb_ma_mode_radio"
            )
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã Combo (Bắt đầu bằng CB)", value=auto_cb_code, key="cb_code_display_auto")
            else:
                ma_lk = st.text_input("Mã Combo (Tự viết)", value=def_ma if def_ma else auto_cb_code, key="cb_code_display_manual")
            so_luong = st.number_input("Số lượng bộ", min_value=0, step=1, value=0, key="cb_sl_input")
        with c2:
            don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Hộp", "Combo"], index=["Bộ", "Hộp", "Combo"].index(def_dv) if def_dv in ["Bộ", "Hộp", "Combo"] else 0, key="cb_dv_input")
            loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"], key="cb_op_input")
            hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)", value=def_img, key="cb_img_input")
        if ma_lk and not df.empty and ma_lk in df["Ma_LK"].values:
            existing_cb_row = df[df["Ma_LK"] == ma_lk].iloc[0]
            st.error(f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã Combo `{ma_lk}` đã tồn tại trong hệ thống (Tên: *{existing_cb_row['Ten_LK']}*, Tồn: *{existing_cb_row['So_luong']}*).")
        ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Cập nhật thêm/bớt linh kiện thành phần combo", key="cb_note_input")
        st.markdown("---")
        st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN")
        def get_tp_val(idx, field):
            if idx < len(def_tp) and isinstance(def_tp, list):
                val = def_tp[idx].get(field, "")
                return val if val is not None else ""
            return ""
        tps_input = []
        generated_codes_in_form = []
        for i in range(1, 11):
            st.markdown(f"**Thành phần {i}**")
            sub_c1, sub_c2 = st.columns([3, 1])
            with sub_c1:
                t_name = st.text_input(
                    f"Tên đầy đủ linh kiện/vật tư {i}", 
                    value=str(get_tp_val(i-1, 'ten')), 
                    key=f"live_tp{i}_ten", 
                    placeholder="VD: Bulong 8.8 mạ nhúng nóng M12x40"
                )
            with sub_c2:
                t_sl = st.number_input(
                    f"Định mức {i}", 
                    min_value=1, 
                    value=int(get_tp_val(i-1, 'sl')) if str(get_tp_val(i-1, 'sl')).isdigit() else 1, 
                    key=f"live_tp{i}_s"
                )
            sub_type_col1, sub_type_col2 = st.columns(2)
            with sub_type_col1:
                item_cat = st.radio(
                    f"Phân loại thành phần {i}:",
                    ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"],
                    horizontal=True,
                    key=f"tp{i}_cat_radio"
                )
            with sub_type_col2:
                tp_ma_choice = st.radio(
                    f"Phương thức mã cho Thành phần {i}:",
                    ["🤖 Hệ thống tự sinh mã", "✍️ Cá nhân tự viết mã"],
                    horizontal=True,
                    key=f"tp{i}_method_radio"
                )
            prefix_type = "LK" if "LK" in item_cat else "VT"
            auto_generated_code = generate_code_from_name(t_name, is_combo=False, item_type=prefix_type)
            old_saved_code = get_tp_val(i-1, 'ma')
            sub_c3, sub_c4 = st.columns([3, 1])
            with sub_c3:
                if tp_ma_choice.startswith("🤖"):
                    final_tp_code = st.text_input(f"Mã linh kiện/vật tư {i}", value=auto_generated_code, key=f"live_tp{i}_code_auto")
                else:
                    final_tp_code = st.text_input(f"Mã linh kiện/vật tư {i} (Tự viết)", value=old_saved_code if old_saved_code else auto_generated_code, key=f"live_tp{i}_code_manual")
            with sub_c4:
                t_img = st.text_input(f"Link ảnh LK/VT {i} (URL)", value=str(get_tp_val(i-1, 'img')), key=f"live_tp{i}_i")
            if final_tp_code:
                if final_tp_code in generated_codes_in_form:
                    st.error(f"⚠️ **Trùng mã nội bộ:** Mã `{final_tp_code}` bị trùng với thành phần bên trên!")
                elif not df.empty and final_tp_code in df["Ma_LK"].values:
                    matched_dup = df[df["Ma_LK"] == final_tp_code].iloc[0]
                    st.info(f"ℹ️ **Thông báo:** Mã `{final_tp_code}` khớp với vật tư đã có trong kho (*{matched_dup['Ten_LK']}* - Tồn: *{matched_dup['So_luong']}*).")
            generated_codes_in_form.append(final_tp_code)
            st.markdown("---")
            tps_input.append({
                "ten": t_name,
                "ma": final_tp_code,
                "sl": int(t_sl),
                "img": t_img.strip() if t_img else ""
            })
        danh_sach_thanh_phan = [item for item in tps_input if item["ten"] and item["ten"].strip() != ""]
        st.markdown("")
        if st.button("💾 Lưu Cấu Hình Combo vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
                    if ghi_chu_tay:
                        nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                    if not df.empty and ma_lk in df["Ma_LK"].values:
                        old_row = df[df["Ma_LK"] == ma_lk].iloc[0]
                        if loai_gd == "📥 Nhập kho mới":
                            so_luong = int(old_row["So_luong"]) + int(so_luong)
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
                    st.session_state.edit_combo_data = None
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
        st.info("💡 Bạn có thể **chọn mã có sẵn từ danh sách** để hệ thống tự điền tên và cập nhật, hoặc **gõ tên sản phẩm mới** để hệ thống tự sinh mã.")
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
                ten_lk = st.text_input("Tên linh kiện / vật tư", value=def_ten, placeholder="VD: Tán 10.9 M16")
                preview_code = generate_code_from_name(ten_lk, is_combo=False) if not def_ma else def_ma
                ma_lk = st.text_input("Mã LK / VT (Tự động sinh hoặc chỉnh sửa)", value=preview_code)
                so_luong = st.number_input("Số lượng nhập thêm / tồn kho", min_value=0, step=1, value=0)
            with c2:
                don_vi = st.selectbox("Đơn vị tính", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"], index=["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"].index(def_dv) if def_dv in ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"] else 0)
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)", value=def_img)
            if ma_lk and selected_existing == "-- Tạo mới / Nhập mới hoàn toàn --" and not df.empty and ma_lk in df["Ma_LK"].values:
                dup_row = df[df["Ma_LK"] == ma_lk].iloc[0]
                st.error(f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã `{ma_lk}` đã tồn tại trong kho với tên **{dup_row['Ten_LK']}** (Tồn: {dup_row['So_luong']}).")
            ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập vật tư lẻ lô mới")
            save_btn = st.form_submit_button("💾 Lưu Linh kiện/Vật tư lẻ vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
                        if ghi_chu_tay:
                            nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                        old_tp = []
                        if not df.empty and ma_lk in df["Ma_LK"].values:
                            old_row = df[df["Ma_LK"] == ma_lk].iloc[0]
                            old_tp = old_row.get("Thanh_phan", [])
                            if loai_gd == "📥 Nhập kho mới":
                                so_luong = int(old_row["So_luong"]) + int(so_luong)
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
                            "Thanh_phan": old_tp
                        }
                        supabase.table("Ton_kho").upsert(new_data).execute()
                        st.success("Đã lưu linh kiện/vật tư lẻ thành công vào Database!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện/vật tư!")
    # 5. XÉ LẺ COMBO THÀNH LINH KIỆN
    elif menu_choice == "🔄 Xé lẻ Combo thành Linh kiện":
        st.title("🔄 XÉ LẺ COMBO THÀNH LINH KIỆN (Kit Breaking)")
        st.markdown("---")
        st.info("💡 Chức năng này giúp bạn tháo dỡ bộ Combo nguyên vẹn: **Giảm số lượng Combo** và **Tự động cộng thêm số lượng linh kiện con** vào kho lẻ để sẵn sàng xuất bán/sửa chữa.")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not combo_df.empty:
                break_options = [f"{row['Ma_LK']} - {row['Ten_LK']} (Tồn: {row['So_luong']} {row['Don_vi']})" for _, row in combo_df.iterrows()]
                selected_break_opt = st.selectbox("1️⃣ Chọn bộ Combo cần xé lẻ", break_options)
                selected_cb_ma = selected_break_opt.split(" - ")[0]
                cb_row = df[df["Ma_LK"] == selected_cb_ma].iloc[0]
                cb_ten = cb_row["Ten_LK"]
                cb_ton = int(cb_row["So_luong"])
                cb_dv = cb_row["Don_vi"]
                cb_tp = cb_row.get("Thanh_phan", [])
                st.warning(f"📦 **Combo chọn:** {cb_ten} (`{selected_cb_ma}`) | Tồn kho: **{cb_ton} {cb_dv}**")
                if cb_tp and isinstance(cb_tp, list) and len(cb_tp) > 0:
                    st.markdown("### 🔗 Các linh kiện con sẽ được cộng vào kho khi xé lẻ:")
                    for tp in cb_tp:
                        sub_m = tp.get('ma')
                        sub_name = tp.get('ten', 'Linh kiện')
                        sub_dinh_muc = int(tp.get('sl', 1))
                        sub_match = df[df["Ma_LK"] == sub_m]
                        sub_current_stock = int(sub_match.iloc[0]["So_luong"]) if not sub_match.empty else 0
                        st.write(f"- `{sub_m}` ({sub_name}) | Định mức/bộ: **{sub_dinh_muc}** | Tồn kho hiện tại: `{sub_current_stock}`")
                    with st.form("break_combo_form"):
                        so_luong_xe = st.number_input("Số lượng bộ Combo muốn xé lẻ", min_value=1, max_value=max(1, cb_ton), step=1, value=1)
                        noi_dung_xe = st.text_input("Ghi chú / Mục đích xé lẻ", placeholder="Ví dụ: Xé lẻ 1 bộ để lấy linh kiện bán lẻ")
                        break_btn = st.form_submit_button("⚡ Xác nhận thực hiện Xé lẻ Combo")
                        if break_btn:
                            try:
                                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                                nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                                cb_ton_moi = cb_ton - int(so_luong_xe)
                                cb_log_moi = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 🔄 Xé lẻ: -{so_luong_xe} {cb_dv} | Ghi chú: {noi_dung_xe}"
                                old_cb_logs = cb_row.get("Nhat_ky", "")
                                if old_cb_logs:
                                    cb_log_moi = old_cb_logs + "\n" + cb_log_moi
                                supabase.table("Ton_kho").update({
                                    "So_luong": cb_ton_moi,
                                    "Nhat_ky": cb_log_moi
                                }).eq("Ma_LK", selected_cb_ma).execute()
                                for tp in cb_tp:
                                    sub_m = tp.get('ma')
                                    sub_sl_tang = int(tp.get('sl', 1)) * int(so_luong_xe)
                                    sub_name_con = tp.get('ten', 'Linh kiện')
                                    sub_row_df = df[df["Ma_LK"] == sub_m]
                                    if not sub_row_df.empty:
                                        sub_row = sub_row_df.iloc[0]
                                        sub_ton_cu = int(sub_row["So_luong"])
                                        sub_ton_moi = sub_ton_cu + sub_sl_tang
                                        sub_dv_con = sub_row.get("Don_vi", "Cái")
                                        sub_img_con = sub_row.get("Hinh_anh", "")
                                        sub_tp_con = sub_row.get("Thanh_phan", [])
                                        sub_logs = sub_row.get("Nhat_ky", "")
                                        sub_log_moi = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - ➕ Nhận từ xé lẻ Combo '{selected_cb_ma}': +{sub_sl_tang} {sub_dv_con}"
                                        if sub_logs:
                                            sub_log_moi = sub_logs + "\n" + sub_log_moi
                                        supabase.table("Ton_kho").upsert({
                                            "Ma_LK": sub_m,
                                            "Ten_LK": sub_name_con,
                                            "So_luong": sub_ton_moi,
                                            "Don_vi": sub_dv_con,
                                            "Nhat_ky": sub_log_moi,
                                            "Hinh_anh": sub_img_con,
                                            "Thanh_phan": sub_tp_con
                                        }).execute()
                                    else:
                                        sub_log_moi = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - ➕ Nhận từ xé lẻ Combo '{selected_cb_ma}': +{sub_sl_tang} Cái"
                                        supabase.table("Ton_kho").upsert({
                                            "Ma_LK": sub_m,
                                            "Ten_LK": sub_name_con,
                                            "So_luong": sub_sl_tang,
                                            "Don_vi": "Cái",
                                            "Nhat_ky": sub_log_moi,
                                            "Hinh_anh": tp.get("img", ""),
                                            "Thanh_phan": []
                                        }).execute()
                                st.success("Xé lẻ Combo thành công! Đã trừ số lượng bộ Combo và tự động cộng bù linh kiện con vào kho lẻ.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi thực hiện xé lẻ: {e}")
                else:
                    st.info("Bộ Combo này chưa khai báo định mức linh kiện thành phần ở Phần 2.")
            else:
                st.warning("Hiện chưa có mã Combo nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 6. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO (Tự động trừ định mức linh kiện/vật tư con)")
        st.markdown("---")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not combo_df.empty:
                export_options = [f"{row['Ma_LK']} - {row['Ten_LK']}" for _, row in combo_df.iterrows()]
                selected_export_opt = st.selectbox("1️⃣ Chọn Combo cần xuất kho", export_options)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
                hien_thi_ten = current_item_row["Ten_LK"]
                ton_hien_tai = current_item_row["So_luong"]
                don_vi_tinh = current_item_row["Don_vi"]
                hinh_anh_cu = current_item_row["Hinh_anh"]
                thanh_phan_list = current_item_row.get("Thanh_phan", [])
                st.warning(f"📦 **Combo chọn:** {hien_thi_ten} (`{selected_export_item}`) | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}**")
                if thanh_phan_list and isinstance(thanh_phan_list, list) and len(thanh_phan_list) > 0:
                    st.info("🔗 **Các linh kiện/vật tư con bên trong sẽ được trừ tự động theo định mức:**")
                    for tp in thanh_phan_list:
                        sub_m = tp.get('ma')
                        sub_name = tp.get('ten', 'Linh kiện')
                        sub_sl = tp.get('sl')
                        sub_img = tp.get('img', '')
                        sub_item = df[df["Ma_LK"] == sub_m]
                        sub_stock = sub_item.iloc[0]["So_luong"] if not sub_item.empty else 0
                        st.write(f"- `{sub_m}` ({sub_name}) | Định mức trừ: **{sub_sl} x SL xuất** | Tồn kho hiện tại: `{sub_stock}`")
                        if sub_img:
                            st.image(sub_img, width=60)
                with st.form("export_combo_form", clear_on_submit=True):
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        so_luong_xuat = st.number_input("Số lượng Combo xuất kho", min_value=1, step=1, value=1)
                    with col_ex2:
                        ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                    noi_dung_xuat = st.text_input("Nội dung / Mục đích xuất kho", placeholder="Ví dụ: Xuất lắp ráp bộ combo")
                    export_btn = st.form_submit_button("Xác nhận Xuất Combo")
                    if export_btn:
                        try:
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                            so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                            nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất Combo: {so_luong_xuat} {don_vi_tinh}"
                            if noi_dung_xuat:
                                nhat_ky_xuat += f" | Nội dung: {noi_dung_xuat}"
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
                            if thanh_phan_list and isinstance(thanh_phan_list, list):
                                for tp in thanh_phan_list:
                                    sub_ma = tp.get('ma')
                                    sub_sl_can_dung = int(tp.get('sl')) * int(so_luong_xuat)
                                    sub_row_df = df[df["Ma_LK"] == sub_ma]
                                    if not sub_row_df.empty:
                                        sub_row = sub_row_df.iloc[0]
                                        sub_ton_cu = int(sub_row["So_luong"])
                                        sub_ton_moi = sub_ton_cu - sub_sl_can_dung
                                        sub_logs = sub_row.get("Nhat_ky", "")
                                        sub_log_moi = f"\n[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📉 Trừ tự động theo Combo '{selected_export_item}': -{sub_sl_can_dung}"
                                        supabase.table("Ton_kho").update({
                                            "So_luong": sub_ton_moi,
                                            "Nhat_ky": sub_logs + sub_log_moi
                                        }).eq("Ma_LK", sub_ma).execute()
                            st.success(f"Xuất kho Combo thành công! Đã trừ định mức linh kiện/vật tư thành phần.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thực hiện xuất kho: {e}")
            else:
                st.warning("Hiện chưa có mã Combo nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 7. XUẤT KHO LINH KIỆN LẺ
    elif menu_choice == "📤 Xuất kho Linh kiện lẻ":
        st.title("📤 XUẤT KHO LINH KIỆN / VẬT TƯ LẺ (Độc lập & Thành phần)")
        st.markdown("---")
        if not df.empty:
            all_items_dict = {}
            for _, row in df.iterrows():
                m = row["Ma_LK"]
                t = row["Ten_LK"]
                dv = row["Don_vi"]
                sl = row["So_luong"]
                img = row.get("Hinh_anh", "")
                if not m.startswith(("CB", "CM")):
                    if m not in all_items_dict:
                        all_items_dict[m] = {"Ten_LK": t, "So_luong": sl, "Don_vi": dv, "Hinh_anh": img}
                tp_list = row.get("Thanh_phan", [])
                if tp_list and isinstance(tp_list, list):
                    for tp in tp_list:
                        sub_m = tp.get("ma")
                        sub_name = tp.get("ten", "Linh kiện")
                        if sub_m and not sub_m.startswith(("CB", "CM")) and sub_m not in all_items_dict:
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_match.empty:
                                all_items_dict[sub_m] = {
                                    "Ten_LK": sub_match.iloc[0]["Ten_LK"],
                                    "So_luong": sub_match.iloc[0]["So_luong"],
                                    "Don_vi": sub_match.iloc[0]["Don_vi"],
                                    "Hinh_anh": sub_match.iloc[0].get("Hinh_anh", "")
                                }
                            else:
                                all_items_dict[sub_m] = {
                                    "Ten_LK": sub_name,
                                    "So_luong": 0,
                                    "Don_vi": "Cái",
                                    "Hinh_anh": tp.get("img", "")
                                }
            export_options = [f"{m} - {info['Ten_LK']}" for m, info in all_items_dict.items()]
            if export_options:
                selected_export_opt = st.selectbox("1️⃣ Chọn linh kiện / vật tư cần xuất kho", export_options)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_info = all_items_dict[selected_export_item]
                hien_thi_ten = current_info["Ten_LK"]
                ton_hien_tai = current_info["So_luong"]
                don_vi_tinh = current_info["Don_vi"]
                hinh_anh_cu = current_info["Hinh_anh"]
                st.warning(f"🔩 **Linh kiện/Vật tư chọn:** {hien_thi_ten} (`{selected_export_item}`) | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}**")
                with st.form("export_item_form", clear_on_submit=True):
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        so_luong_xuat = st.number_input("Số lượng xuất kho", min_value=1, step=1, value=1)
                    with col_ex2:
                        ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                    noi_dung_xuat = st.text_input("Nội dung / Mục đích xuất kho", placeholder="Ví dụ: Xuất vật tư sửa chữa lẻ")
                    export_btn = st.form_submit_button("Xác nhận Xuất Linh kiện/Vật tư")
                    if export_btn:
                        try:
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                            so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                            nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất lẻ: {so_luong_xuat} {don_vi_tinh}"
                            if noi_dung_xuat:
                                nhat_ky_xuat += f" | Nội dung: {noi_dung_xuat}"
                            check_exist = df[df["Ma_LK"] == selected_export_item]
                            if not check_exist.empty:
                                old_logs = check_exist.iloc[0].get("Nhat_ky", "")
                                if old_logs:
                                    nhat_ky_xuat = old_logs + "\n" + nhat_ky_xuat
                                old_tp = check_exist.iloc[0].get("Thanh_phan", [])
                            else:
                                old_tp = []
                            update_data = {
                                "Ma_LK": selected_export_item,
                                "Ten_LK": hien_thi_ten,
                                "So_luong": so_luong_moi,
                                "Don_vi": don_vi_tinh,
                                "Nhat_ky": nhat_ky_xuat,
                                "Hinh_anh": hinh_anh_cu,
                                "Thanh_phan": old_tp
                            }
                            supabase.table("Ton_kho").upsert(update_data).execute()
                            for _, combo_row in df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)].iterrows():
                                cb_ma = combo_row["Ma_LK"]
                                cb_tp_list = combo_row.get("Thanh_phan", [])
                                if cb_tp_list and isinstance(cb_tp_list, list):
                                    for tp in cb_tp_list:
                                        if tp.get("ma") == selected_export_item:
                                            dinh_muc = int(tp.get("sl", 1))
                                            so_bo_giam = so_luong_xuat // dinh_muc
                                            if so_bo_giam > 0:
                                                cb_ton_hien_tai = int(combo_row["So_luong"])
                                                cb_ton_moi = max(0, cb_ton_hien_tai - so_bo_giam)
                                                cb_logs = combo_row.get("Nhat_ky", "")
                                                cb_log_moi = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📉 Tự động giảm do xuất lẻ linh kiện '{selected_export_item}': -{so_bo_giam} {combo_row['Don_vi']}"
                                                if cb_logs:
                                                    cb_log_moi = cb_logs + "\n" + cb_log_moi
                                                supabase.table("Ton_kho").update({
                                                    "So_luong": cb_ton_moi,
                                                    "Nhat_ky": cb_log_moi
                                                }).eq("Ma_LK", cb_ma).execute()
                            st.success(f"Xuất linh kiện lẻ thành công! Hệ thống đã tự động đồng bộ giảm số lượng bộ Combo tương ứng.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thực hiện xuất kho: {e}")
            else:
                st.warning("Hiện chưa có mã linh kiện/vật tư nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 8. BÁO CÁO & XUẤT EXCEL
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 BÁO CÁO KHO & XUẤT FILE EXCEL")
        st.markdown("---")
        st.info("💡 Bạn có thể tải toàn bộ dữ liệu tồn kho và nhật ký nhập/xuất kho dưới dạng file **Excel (.xlsx)** để lưu trữ hoặc phục vụ kiểm kê hàng tháng.")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi"]].copy()
                df_ton_kho.columns = ["Mã Sản Phẩm / Combo", "Tên Sản Phẩm", "Số Lượng Tồn Kho", "Đơn Vị Tính"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho_Hien_Tai', index=False)
                df_nhat_ky = df[["Ma_LK", "Ten_LK", "Nhat_ky"]].copy()
                df_nhat_ky.columns = ["Mã Sản Phẩm", "Tên Sản Phẩm", "Lịch Sử Nhật Ký Chi Tiết"]
                df_nhat_ky.to_excel(writer, sheet_name='Lich_Su_Nhat_Ky', index=False)
            excel_data = output.getvalue()
            time_stamp = datetime.now().strftime("%Y%m%d_%H%M")
            col_rep1, col_rep2 = st.columns(2)
            with col_rep1:
                st.markdown("### 📊 Thống kê nhanh")
                st.metric("Tổng số mặt hàng / Combo", len(df))
                st.metric("Tổng lượng kho", int(df["So_luong"].sum()) if "So_luong" in df else 0)
            with col_rep2:
                st.markdown("### 📥 Tải Báo Cáo")
                st.download_button(
                    label="📥 Tải Báo Cáo Kho Dạng Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"Bao_Cao_Kho_{time_stamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("Kho hiện đang trống, chưa có dữ liệu để xuất báo cáo!")
