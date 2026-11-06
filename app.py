import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
import io
import re
import unicodedata
# Cấu hình giao diện toàn màn hình
st.set_page_config(page_title="Quản Lý Kho Cá Nhân", page_icon="📦", layout="wide")
# CSS căn giữa toàn bộ bảng trong Streamlit
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div[role="grid"] div[role="gridcell"] {
        text-align: center !important;
        justify-content: center !important;
    }
    div[data-testid="stDataFrame"] div[role="grid"] div[role="columnheader"] {
        text-align: center !important;
        justify-content: center !important;
    }
    </style>
""", unsafe_allow_html=True)
# Khởi tạo kết nối Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase: Client = init_supabase()
# Tải dữ liệu tồn kho
@st.cache_data(ttl=0)
def load_data():
    try:
        response = supabase.table("Ton_kho").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Hàm định dạng tiền tệ chuẩn kế toán Việt Nam
def format_money(val):
    try:
        if pd.isna(val) or val == "":
            return "0"
        num = float(val)
        return f"{num:,.0f}".replace(",", ".")
    except Exception:
        return "0"
# Hàm loại bỏ dấu tiếng Việt
def remove_vietnamese_accent(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return text
# Hàm tự động sinh mã thông minh
def generate_code_from_name(full_name, is_combo=False, item_type="VT"):
    if not full_name or not full_name.strip():
        return ""
    clean_no_accent = remove_vietnamese_accent(full_name.strip())
    upper_name = clean_no_accent.upper()
    if is_combo:
        clean_code = re.sub(r'[^A-Z0-9\.]', '_', upper_name)
        clean_code = re.sub(r'_+', '_', clean_code).strip('_')
        parts = clean_code.split('_')
        short_str = "_".join(parts[:3]) if len(parts) > 3 else clean_code
        return f"CB-{short_str[:25]}"
    prefix = item_type if item_type in ["LK", "VT"] else "VT"
    upper_name = upper_name.replace("BULONG", "BL").replace("BU LONG", "BL")
    upper_name = upper_name.replace("LONG DEN", "LD").replace("LON DEN", "LD")
    clean_code = re.sub(r'[^A-Z0-9\.]', '_', upper_name)
    clean_code = re.sub(r'_+', '_', clean_code).strip('_')
    auto_code = f"{prefix}-{clean_code[:30]}"
    return auto_code.replace("__", "_").upper()
# Quản lý đăng nhập
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
        "✏️ Điều chỉnh thông tin & Giá Combo",
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
        if not df.empty:
            df_filtered = df[df["So_luong"] >= 0].copy()
            for col_check in ["Gia_nhap", "Gia_xuat", "Barcode", "Quy_cach", "So_luong"]:
                if col_check not in df_filtered.columns:
                    df_filtered[col_check] = 1 if col_check == "Quy_cach" else (0 if "Gia" in col_check or col_check == "So_luong" else "")
            df_filtered["Thanh_tien"] = pd.to_numeric(df_filtered["So_luong"], errors="coerce").fillna(0) * pd.to_numeric(df_filtered["Gia_nhap"], errors="coerce").fillna(0)
            tong_gia_tri_kho = df_filtered["Thanh_tien"].sum()
            tong_so_luong = int(df_filtered["So_luong"].sum())
            col_m1, col_m2, col_m3 = st.columns([2, 2, 3])
            with col_m1:
                st.metric(label="📊 TỔNG MẶT HÀNG IN KHO", value=f"{len(df_filtered)} sản phẩm")
            with col_m2:
                st.metric(label="📦 TỔNG SỐ LƯỢNG TỒN", value=f"{format_money(tong_so_luong)} đơn vị")
            with col_m3:
                st.metric(label="💰 TỔNG GIÁ TRỊ TỒN KHO", value=f"{format_money(tong_gia_tri_kho)} VNĐ")
            st.markdown("---")
            df_filtered["Gia_nhap_fmt"] = df_filtered["Gia_nhap"].apply(format_money)
            df_filtered["Gia_xuat_fmt"] = df_filtered["Gia_xuat"].apply(format_money)
            df_display = df_filtered[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt", "Barcode"]].copy()
            df_display.columns = ["Mã sản phẩm", "Tên sản phẩm", "Tồn kho", "Đơn vị cơ bản", "Quy cách (SL/Kiện)", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)", "Mã vạch (Barcode)"]
            st.dataframe(df_display, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm linh kiện mới ở mục bên trái!")
    # 2. TRA CỨU & LỌC CHI TIẾT
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU & LỌC CHI TIẾT SẢN PHẨM")
        st.markdown("---")
        if not df.empty:
            col_sc1, col_sc2 = st.columns([2, 2])
            with col_sc1:
                barcode_search = st.text_input("🪪 Quét / Nhập mã vạch (Barcode) để tra cứu nhanh", placeholder="Nhấn vào đây rồi quét mã vạch...")
            target_ma_lk = None
            if barcode_search.strip():
                matched_bc = df[df["Barcode"].str.contains(barcode_search.strip(), case=False, na=False)]
                if not matched_bc.empty:
                    target_ma_lk = matched_bc.iloc[0]["Ma_LK"]
                    st.success(f"✨ Đã tìm thấy sản phẩm qua mã vạch: **{matched_bc.iloc[0]['Ten_LK']}** (`{target_ma_lk}`)")
                else:
                    st.warning("⚠️ Không tìm thấy sản phẩm nào khớp với mã vạch này.")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                loai_loc = st.selectbox(
                    "Lọc theo danh mục hoạt động", 
                    ["Tất cả", "📥 Nhập kho", "📤 Xuất kho", "🔄 Cập nhật thông tin"]
                )
            with col_f2:
                ma_list = df["Ma_LK"].tolist()
                default_idx = ma_list.index(target_ma_lk) if target_ma_lk in ma_list else 0
                selected_item = st.selectbox("Chọn mã linh kiện", ma_list, index=default_idx)
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
                    st.write(f"**📦 Quy cách đóng gói:** 1 Kiện = {item_row.get('Quy_cach', 1)} {item_row.get('Don_vi', 'Cái')}")
                    st.write(f"**💰 Giá nhập:** {format_money(item_row.get('Gia_nhap', 0))} VNĐ")
                    st.write(f"**🏷️ Giá xuất:** {format_money(item_row.get('Gia_xuat', 0))} VNĐ")
                    st.write(f"**🪪 Mã vạch (Barcode):** `{item_row.get('Barcode', 'Chưa có')}`")
                    thanh_phan = item_row.get('Thanh_phan', None)
                    if thanh_phan and isinstance(thanh_phan, list) and len(thanh_phan) > 0:
                        st.markdown("**🔗 Các linh kiện/vật tư thành phần trong bộ:**")
                        for tp in thanh_phan:
                            sub_m = tp.get('ma')
                            sub_name = tp.get('ten', '')
                            sub_sl = tp.get('sl')
                            sub_dv = tp.get('dv', 'Cái')
                            sub_gia = tp.get('gia', 0)
                            sub_img = tp.get('img', '')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_name and not sub_match.empty:
                                sub_name = sub_match.iloc[0]["Ten_LK"]
                            gia_str = f" | Giá: **{format_money(sub_gia)} VNĐ**" if sub_gia else ""
                            st.write(f"- `{sub_m}` ({sub_name}) | Định mức: **{sub_sl} {sub_dv}**{gia_str}")
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
    # 3. ĐIỀU CHỈNH THÔNG TIN & GIÁ COMBO
    elif menu_choice == "✏️ Điều chỉnh thông tin & Giá Combo":
        st.title("✏️ ĐIỀU CHỈNH THÔNG TIN, GIÁ & THÀNH PHẦN COMBO")
        st.markdown("---")
        if "selected_cb_to_edit" not in st.session_state:
            st.session_state.selected_cb_to_edit = ""
        combo_dict = {}
        if not df.empty:
            c_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            for _, r in c_df.iterrows():
                d_str = f"{r['Ma_LK']} - {r['Ten_LK']}"
                combo_dict[d_str] = r.to_dict()
        if combo_dict:
            col_load1, col_load2 = st.columns([3, 1])
            with col_load1:
                chosen_combo_str = st.selectbox("📂 Chọn mã Combo cần chỉnh sửa:", list(combo_dict.keys()), key="select_combo_dropdown")
            with col_load2:
                st.write("")
                st.write("")
                if st.button("📥 Nạp dữ liệu cũ lên Form", type="secondary"):
                    st.session_state.selected_cb_to_edit = chosen_combo_str.split(" - ")[0]
                    st.success(f"Đã nạp dữ liệu của `{st.session_state.selected_cb_to_edit}` lên form!")
                    st.rerun()
        else:
            st.warning("Chưa có mã Combo nào trong hệ thống!")
        active_data = {}
        target_cb_code = st.session_state.selected_cb_to_edit
        if target_cb_code and not df.empty:
            matched_rows = df[df["Ma_LK"] == target_cb_code]
            if not matched_rows.empty:
                active_data = matched_rows.iloc[0].to_dict()
        def_ma = active_data.get("Ma_LK", "")
        def_ten = active_data.get("Ten_LK", "")
        def_dv = active_data.get("Don_vi", "Bộ")
        def_img = active_data.get("Hinh_anh", "")
        def_tp = active_data.get("Thanh_phan", [])
        def_gianhap = int(active_data.get("Gia_nhap", 0)) if active_data.get("Gia_nhap") else 0
        def_giaxuat = int(active_data.get("Gia_xuat", 0)) if active_data.get("Gia_xuat") else 0
        def_barcode = active_data.get("Barcode", "") if active_data.get("Barcode") else ""
        def_quycach = int(active_data.get("Quy_cach", 1)) if active_data.get("Quy_cach") else 1
        if target_cb_code:
            st.info(f"Đang thao tác chỉnh sửa cho Combo: **{target_cb_code}**")
        with st.form("edit_combo_form_final"):
            c1, c2 = st.columns(2)
            with c1:
                ten_lk_e = st.text_input("Tên Combo", value=def_ten)
                ma_lk_e = st.text_input("Mã Combo (Cố định)", value=def_ma, disabled=True)
                quy_cach_e = st.number_input("Quy cách: 1 Kiện = ? Đơn vị lẻ", min_value=1, step=1, value=def_quycach)
                barcode_e = st.text_input("Mã vạch (Barcode)", value=def_barcode)
            with c2:
                dv_list = ["Bộ", "Hộp", "Combo"]
                dv_idx = dv_list.index(def_dv) if def_dv in dv_list else 0
                don_vi_e = st.selectbox("Đơn vị tính cơ bản", dv_list, index=dv_idx)
                gia_nhap_e = st.number_input("Giá nhập Combo (VNĐ)", min_value=0, step=1000, value=def_gianhap, format="%d")
                gia_xuat_e = st.number_input("Giá xuất Combo (VNĐ)", min_value=0, step=1000, value=def_giaxuat, format="%d")
                hinh_anh_e = st.text_input("Link ảnh chi tiết (URL)", value=def_img)
            ghi_chu_e = st.text_input("Ghi chú điều chỉnh", placeholder="Ví dụ: Cập nhật tăng giá bán và giá nhập mới")
            st.markdown("---")
            st.markdown("### 🧩 THÀNH PHẦN COMBO HIỆN TẠI & GIÁ CHI TIẾT")
            def get_tp_val_e(idx, field):
                if idx < len(def_tp) and isinstance(def_tp, list):
                    val = def_tp[idx].get(field, "")
                    return val if val is not None else ""
                return ""
            tps_input_e = []
            for i in range(1, 11):
                st.markdown(f"**Thành phần {i}**")
                sub_c1, sub_c2, sub_c_dv, sub_c_gia = st.columns([3, 1, 1, 1.5])
                with sub_c1:
                    t_name_e = st.text_input(f"Tên linh kiện {i}", value=str(get_tp_val_e(i-1, 'ten')), key=f"ef_tp_{i}_ten")
                with sub_c2:
                    t_sl_e = st.number_input(f"Định mức {i}", min_value=1, value=int(get_tp_val_e(i-1, 'sl')) if str(get_tp_val_e(i-1, 'sl')).isdigit() else 1, key=f"ef_tp_{i}_sl")
                with sub_c_dv:
                    old_dv_e = get_tp_val_e(i-1, 'dv')
                    dv_sub_list = ["Cái", "Chiếc", "Bộ", "Kg", "Mét", "Túi", "Hộp", "Cuộn"]
                    dv_s_idx_e = dv_sub_list.index(old_dv_e) if old_dv_e in dv_sub_list else 0
                    t_dv_e = st.selectbox(f"Đơn vị {i}", dv_sub_list, index=dv_s_idx_e, key=f"ef_tp_{i}_dv")
                with sub_c_gia:
                    old_gia_e = get_tp_val_e(i-1, 'gia')
                    val_gia = int(old_gia_e) if old_gia_e and str(old_gia_e).replace('.','',1).isdigit() else 0
                    t_gia_e = st.number_input(f"Giá linh kiện {i} (VNĐ)", min_value=0, step=1000, value=val_gia, format="%d", key=f"ef_tp_{i}_gia")
                old_code_e = get_tp_val_e(i-1, 'ma')
                sub_c3, sub_c4 = st.columns([3, 1])
                with sub_c3:
                    final_tp_code_e = st.text_input(f"Mã linh kiện {i}", value=old_code_e if old_code_e else generate_code_from_name(t_name_e, is_combo=False), key=f"ef_tp_{i}_ma")
                with sub_c4:
                    t_img_e = st.text_input(f"Link ảnh {i}", value=str(get_tp_val_e(i-1, 'img')), key=f"ef_tp_{i}_img")
                st.markdown("---")
                tps_input_e.append({
                    "ten": t_name_e,
                    "ma": final_tp_code_e,
                    "sl": int(t_sl_e),
                    "dv": t_dv_e,
                    "gia": int(t_gia_e),
                    "img": t_img_e.strip() if t_img_e else ""
                })
            danh_sach_thanh_phan_e = [item for item in tps_input_e if item["ten"] and item["ten"].strip() != ""]
            submit_edit = st.form_submit_button("💾 Cập nhật Thay đổi vào Database", type="primary", use_container_width=True)
            if submit_edit:
                if target_cb_code:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        old_row = df[df["Ma_LK"] == target_cb_code].iloc[0]
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 🔄 Cập nhật thông tin & Giá"
                        if ghi_chu_e:
                            nhat_ky_str += f" | Ghi chú: {ghi_chu_e}"
                        old_logs = old_row.get("Nhat_ky", "")
                        if old_logs:
                            nhat_ky_str = old_logs + "\n" + nhat_ky_str
                        update_data = {
                            "Ma_LK": target_cb_code,
                            "Ten_LK": ten_lk_e,
                            "So_luong": int(old_row["So_luong"]),
                            "Don_vi": don_vi_e,
                            "Nhat_ky": nhat_ky_str,
                            "Hinh_anh": hinh_anh_e,
                            "Thanh_phan": danh_sach_thanh_phan_e,
                            "Gia_nhap": float(gia_nhap_e),
                            "Gia_xuat": float(gia_xuat_e),
                            "Barcode": barcode_e.strip(),
                            "Quy_cach": int(quy_cach_e)
                        }
                        supabase.table("Ton_kho").upsert(update_data).execute()
                        st.success("Đã cập nhật thông tin và giá thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi cập nhật: {e}")
                else:
                    st.warning("Vui lòng bấm nút 'Nạp dữ liệu cũ lên Form' trước khi lưu!")
    # 4. NHẬP MỚI COMBO
    elif menu_choice == "📥 Nhập mới Combo":
        st.title("📦 KHAI BÁO & NHẬP MỚI COMBO SẢN PHẨM")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input("Tên Combo", placeholder="VD: Bộ bàn gỗ lim 1.2M", key="new_cb_ten")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            cb_ma_mode = st.radio("Phương thức mã Combo:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_cb_mode")
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã Combo (Tự động)", value=auto_cb_code, key="new_cb_autocode")
            else:
                ma_lk = st.text_input("Mã Combo (Tự viết)", value=auto_cb_code, key="new_cb_manualcode")
            don_vi = st.selectbox("Đơn vị tính cơ bản của Combo", ["Bộ", "Hộp", "Combo"], key="new_cb_dv")
            hinh_thuc_nhap_cb = st.radio(
                "Hình thức nhập kho:",
                ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"],
                horizontal=True,
                key="new_cb_hinh_thuc"
            )
            so_luong_nhap = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="new_cb_sl")
            if "📦" in hinh_thuc_nhap_cb:
                quy_cach = st.number_input("Quy cách: 1 Kiện = ? Đơn vị cơ bản", min_value=1, step=1, value=1, key="new_cb_qc")
                so_luong_thuc_te = so_luong_nhap * quy_cach
                st.info(f"💡 Quy đổi theo kiện: **{so_luong_nhap} Kiện** x {quy_cach} = **{so_luong_thuc_te} {don_vi}** sẽ được cộng vào kho.")
            else:
                quy_cach = 1
                so_luong_thuc_te = so_luong_nhap
                st.info(f"💡 Nhập trực tiếp: **{so_luong_thuc_te} {don_vi}** sẽ được cộng vào kho.")
            barcode = st.text_input("Mã vạch (Barcode)", placeholder="Quét hoặc nhập mã vạch...", key="new_cb_bc")
        with c2:
            gia_nhap = st.number_input("Giá nhập Combo (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_cb_gn")
            gia_xuat = st.number_input("Giá xuất Combo (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_cb_gx")
            hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)", key="new_cb_img")
        if ma_lk and not df.empty and ma_lk in df["Ma_LK"].values:
            st.error(f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã Combo `{ma_lk}` đã tồn tại trong hệ thống!")
        ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập mới lô combo đầu năm", key="new_cb_note")
        st.markdown("---")
        st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN & GIÁ CHI TIẾT")
        tps_input = []
        for i in range(1, 11):
            st.markdown(f"**Thành phần {i}**")
            # Khởi tạo session_state cho từng thành phần
            tname_key = f"tp_{i}_name"
            tmode_key = f"tp_{i}_mode"
            ttype_key = f"tp_{i}_type"
            tma_key = f"tp_{i}_code"
            if tname_key not in st.session_state:
                st.session_state[tname_key] = ""
            if tmode_key not in st.session_state:
                st.session_state[tmode_key] = "🤖 Tự sinh"
            if ttype_key not in st.session_state:
                st.session_state[ttype_key] = "🔩 Vật tư (VT)"
            if tma_key not in st.session_state:
                st.session_state[tma_key] = ""
            # Hàm callback tự động cập nhật mã khi tên thay đổi
            def make_name_change_cb(idx=i):
                def callback():
                    mode = st.session_state.get(f"tp_{idx}_mode", "🤖 Tự sinh")
                    if mode.startswith("🤖"):
                        curr_name = st.session_state.get(f"tp_{idx}_name", "")
                        cat = st.session_state.get(f"tp_{idx}_type", "🔩 Vật tư (VT)")
                        prefix = "LK" if "LK" in cat else "VT"
                        st.session_state[f"tp_{idx}_code"] = generate_code_from_name(curr_name, is_combo=False, item_type=prefix)
                return callback
            sub_c1, sub_c2, sub_c_dv, sub_c_gia = st.columns([3, 1, 1, 1.5])
            with sub_c1:
                t_name = st.text_input(
                    f"Tên linh kiện {i}", 
                    placeholder="VD: Bulong M24", 
                    key=tname_key,
                    on_change=make_name_change_cb(i)
                )
            with sub_c2:
                t_sl = st.number_input(f"Định mức {i}", min_value=1, value=1, key=f"new_tp_{i}_sl")
            with sub_c_dv:
                t_dv = st.selectbox(f"Đơn vị {i}", ["Cái", "Chiếc", "Bộ", "Kg", "Mét", "Túi", "Hộp", "Cuộn"], key=f"new_tp_{i}_dv")
            with sub_c_gia:
                t_gia = st.number_input(f"Giá linh kiện {i} (VNĐ)", min_value=0, step=1000, value=0, format="%d", key=f"new_tp_{i}_gia")
            # Bổ sung hàng lựa chọn Phân loại và Phương thức tạo mã tương tự Phần 1
            col_tp_type, col_tp_mode = st.columns(2)
            with col_tp_type:
                item_cat_tp = st.radio(
                    f"Phân loại thành phần {i}:",
                    ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"],
                    horizontal=True,
                    key=ttype_key,
                    on_change=make_name_change_cb(i)
                )
            with col_tp_mode:
                item_mode_tp = st.radio(
                    f"Phương thức mã thành phần {i}:",
                    ["🤖 Tự sinh", "✍️ Tự viết"],
                    horizontal=True,
                    key=tmode_key,
                    on_change=make_name_change_cb(i)
                )
            prefix_tp = "LK" if "LK" in item_cat_tp else "VT"
            auto_code_tp = generate_code_from_name(t_name, is_combo=False, item_type=prefix_tp)
            sub_c3, sub_c4 = st.columns([3, 1])
            with sub_c3:
                if item_mode_tp.startswith("🤖"):
                    final_tp_code = st.text_input(f"Mã linh kiện {i} (Tự động từ hệ thống)", value=auto_code_tp, key=f"tp_{i}_show_auto", disabled=True)
                else:
                    final_tp_code = st.text_input(f"Mã linh kiện {i} (Cá nhân tự viết)", key=tma_key)
            with sub_c4:
                t_img = st.text_input(f"Link ảnh {i}", key=f"new_tp_{i}_img")
            st.markdown("---")
            tps_input.append({
                "ten": t_name,
                "ma": final_tp_code,
                "sl": int(t_sl),
                "dv": t_dv,
                "gia": int(t_gia),
                "img": t_img.strip() if t_img else ""
            })
        danh_sach_thanh_phan = [item for item in tps_input if item["ten"] and item["ten"].strip() != ""]
        st.markdown("")
        if st.button("💾 Lưu Mới Combo vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho mới: {so_luong_thuc_te} {don_vi}"
                    if ghi_chu_tay:
                        nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                    new_data = {
                        "Ma_LK": ma_lk,
                        "Ten_LK": ten_lk,
                        "So_luong": int(so_luong_thuc_te),
                        "Don_vi": don_vi,
                        "Nhat_ky": nhat_ky_str,
                        "Hinh_anh": hinh_anh,
                        "Thanh_phan": danh_sach_thanh_phan,
                        "Gia_nhap": float(gia_nhap),
                        "Gia_xuat": float(gia_xuat),
                        "Barcode": barcode.strip(),
                        "Quy_cach": int(quy_cach)
                    }
                    supabase.table("Ton_kho").upsert(new_data).execute()
                    st.success("Đã tạo mới Combo thành công vào Database!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu dữ liệu: {e}")
            else:
                st.warning("Vui lòng điền đầy đủ Mã và Tên Combo!")
    # 5. NHẬP MỚI LINH KIỆN LẺ
    elif menu_choice == "📥 Nhập mới Linh kiện lẻ":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        existing_items = ["-- Tạo mới / Nhập mới hoàn toàn --"]
        item_dict = {}
        if not df.empty:
            df_le = df[~df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            for _, r in df_le.iterrows():
                display_str = f"{r['Ma_LK']} - {r['Ten_LK']}"
                existing_items.append(display_str)
                item_dict[display_str] = r.to_dict()
        if "le_selected_val" not in st.session_state:
            st.session_state.le_selected_val = "-- Tạo mới / Nhập mới hoàn toàn --"
        def on_le_select_change():
            sel = st.session_state.get("le_sel_box", "-- Tạo mới / Nhập mới hoàn toàn --")
            if sel != "-- Tạo mới / Nhập mới hoàn toàn --":
                row_data = item_dict[sel]
                st.session_state.le_ten_input_val = row_data.get("Ten_LK", "")
                st.session_state.le_ma_input_val = row_data.get("Ma_LK", "")
                st.session_state.le_dv_input_val = row_data.get("Don_vi", "Cái")
                st.session_state.le_img_input_val = row_data.get("Hinh_anh", "")
                st.session_state.le_gianhap_val = int(row_data.get("Gia_nhap", 0)) if row_data.get("Gia_nhap") else 0
                st.session_state.le_giaxuat_val = int(row_data.get("Gia_xuat", 0)) if row_data.get("Gia_xuat") else 0
                st.session_state.le_barcode_val = row_data.get("Barcode", "") if row_data.get("Barcode") else ""
                st.session_state.le_quycach_val = int(row_data.get("Quy_cach", 1)) if row_data.get("Quy_cach") else 1
                st.session_state.single_item_method_radio = "✍️ Tự viết"
            else:
                st.session_state.le_ten_input_val = ""
                st.session_state.le_ma_input_val = ""
                st.session_state.le_dv_input_val = "Cái"
                st.session_state.le_img_input_val = ""
                st.session_state.le_gianhap_val = 0
                st.session_state.le_giaxuat_val = 0
                st.session_state.le_barcode_val = ""
                st.session_state.le_quycach_val = 1
                st.session_state.single_item_method_radio = "🤖 Tự sinh"
        selected_existing = st.selectbox(
            "🔍 Chọn mã linh kiện/vật tư có sẵn (hoặc chọn 'Tạo mới')", 
            existing_items,
            key="le_sel_box",
            on_change=on_le_select_change
        )
        if "le_ten_input_val" not in st.session_state:
            st.session_state.le_ten_input_val = ""
        if "le_ma_input_val" not in st.session_state:
            st.session_state.le_ma_input_val = ""
        if "le_dv_input_val" not in st.session_state:
            st.session_state.le_dv_input_val = "Cái"
        if "le_img_input_val" not in st.session_state:
            st.session_state.le_img_input_val = ""
        if "le_gianhap_val" not in st.session_state:
            st.session_state.le_gianhap_val = 0
        if "le_giaxuat_val" not in st.session_state:
            st.session_state.le_giaxuat_val = 0
        if "le_barcode_val" not in st.session_state:
            st.session_state.le_barcode_val = ""
        if "le_quycach_val" not in st.session_state:
            st.session_state.le_quycach_val = 1
        if "single_item_method_radio" not in st.session_state:
            st.session_state.single_item_method_radio = "🤖 Tự sinh"
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input(
                "Tên linh kiện / vật tư", 
                value=st.session_state.le_ten_input_val, 
                placeholder="VD: Bulong 10.9 mạ dacromet M24x90",
                key="le_ten_widget"
            )
            if ten_lk != st.session_state.le_ten_input_val:
                st.session_state.le_ten_input_val = ten_lk
                st.rerun()
            sub_col_type, sub_col_method = st.columns(2)
            with sub_col_type:
                item_cat_le = st.radio(
                    "Phân loại:",
                    ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"],
                    horizontal=True,
                    key="single_item_cat_radio"
                )
            with sub_col_method:
                item_method_le = st.radio(
                    "Phương thức mã:",
                    ["🤖 Tự sinh", "✍️ Tự viết"],
                    horizontal=True,
                    key="single_item_method_radio"
                )
            prefix_type_le = "LK" if "LK" in item_cat_le else "VT"
            auto_code_le = generate_code_from_name(st.session_state.le_ten_input_val, is_combo=False, item_type=prefix_type_le)
            if item_method_le.startswith("🤖"):
                ma_lk = st.text_input("Mã LK / VT (Mã tự động từ hệ thống)", value=auto_code_le, key="le_code_auto_show")
            else:
                manual_default = st.session_state.le_ma_input_val if st.session_state.le_ma_input_val else auto_code_le
                ma_lk = st.text_input("Mã LK / VT (Cá nhân tự viết)", value=manual_default, key="le_code_manual_show")
                st.session_state.le_ma_input_val = ma_lk
            dv_list_le = ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét", "Bộ"]
            current_dv = st.session_state.le_dv_input_val
            dv_idx = dv_list_le.index(current_dv) if current_dv in dv_list_le else 0
            don_vi = st.selectbox("Đơn vị tính cơ bản", dv_list_le, index=dv_idx, key="le_dv_input")
            hinh_thuc_nhap_le = st.radio(
                "Hình thức nhập kho:",
                ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"],
                horizontal=True,
                key="le_hinh_thuc"
            )
            so_luong_nhap_le = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="le_sl_input")
            if "📦" in hinh_thuc_nhap_le:
                quy_cach_le = st.number_input("Quy cách: 1 Kiện = ? Đơn vị cơ bản", min_value=1, step=1, value=st.session_state.le_quycach_val, key="le_quycach_input")
                so_luong_thuc_te_le = so_luong_nhap_le * quy_cach_le
                st.info(f"💡 Quy đổi theo kiện: **{so_luong_nhap_le} Kiện** x {quy_cach_le} = **{so_luong_thuc_te_le} {don_vi}** sẽ được cộng vào kho.")
            else:
                quy_cach_le = 1
                so_luong_thuc_te_le = so_luong_nhap_le
                st.info(f"💡 Nhập trực tiếp: **{so_luong_thuc_te_le} {don_vi}** sẽ được cộng vào kho.")
            barcode = st.text_input("Mã vạch (Barcode)", value=st.session_state.le_barcode_val, placeholder="Quét hoặc nhập mã vạch...", key="le_barcode_widget")
        with c2:
            loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"], key="le_op_input")
            gia_nhap = st.number_input("Giá nhập (VNĐ)", min_value=0, step=1000, value=st.session_state.le_gianhap_val, format="%d", key="le_gianhap_widget")
            gia_xuat = st.number_input("Giá xuất (VNĐ)", min_value=0, step=1000, value=st.session_state.le_giaxuat_val, format="%d", key="le_giaxuat_widget")
            hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)", value=st.session_state.le_img_input_val, key="le_img_input")
        if ma_lk and selected_existing == "-- Tạo mới / Nhập mới hoàn toàn --" and not df.empty and ma_lk in df["Ma_LK"].values:
            dup_row = df[df["Ma_LK"] == ma_lk].iloc[0]
            st.error(f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã `{ma_lk}` đã tồn tại trong kho với tên **{dup_row['Ten_LK']}** (Tồn: {dup_row['So_luong']}).")
        ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập vật tư lẻ lô mới", key="le_note_input")
        st.markdown("")
        if st.button("💾 Lưu Linh kiện/Vật tư lẻ vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong_thuc_te_le} {don_vi}"
                    if ghi_chu_tay:
                        nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                    old_tp = []
                    current_stock_le = so_luong_thuc_te_le
                    if not df.empty and ma_lk in df["Ma_LK"].values:
                        old_row = df[df["Ma_LK"] == ma_lk].iloc[0]
                        old_tp = old_row.get("Thanh_phan", [])
                        if loai_gd == "📥 Nhập kho mới":
                            current_stock_le = int(old_row["So_luong"]) + int(so_luong_thuc_te_le)
                        old_logs = old_row.get("Nhat_ky", "")
                        if old_logs:
                            nhat_ky_str = old_logs + "\n" + nhat_ky_str
                    new_data = {
                        "Ma_LK": ma_lk,
                        "Ten_LK": ten_lk,
                        "So_luong": int(current_stock_le),
                        "Don_vi": don_vi,
                        "Nhat_ky": nhat_ky_str,
                        "Hinh_anh": hinh_anh,
                        "Thanh_phan": old_tp,
                        "Gia_nhap": float(gia_nhap),
                        "Gia_xuat": float(gia_xuat),
                        "Barcode": barcode.strip(),
                        "Quy_cach": int(quy_cach_le)
                    }
                    supabase.table("Ton_kho").upsert(new_data).execute()
                    st.success("Đã lưu linh kiện/vật tư lẻ thành công vào Database!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu dữ liệu: {e}")
            else:
                st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện/vật tư!")
    # 6. XÉ LẺ COMBO THÀNH LINH KIỆN
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
                        sub_dv_con = tp.get('dv', 'Cái')
                        sub_match = df[df["Ma_LK"] == sub_m]
                        sub_current_stock = int(sub_match.iloc[0]["So_luong"]) if not sub_match.empty else 0
                        st.write(f"- `{sub_m}` ({sub_name}) | Định mức/bộ: **{sub_dinh_muc} {sub_dv_con}** | Tồn kho hiện tại: `{sub_current_stock}`")
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
                                    sub_dv_con = tp.get('dv', 'Cái')
                                    sub_row_df = df[df["Ma_LK"] == sub_m]
                                    if not sub_row_df.empty:
                                        sub_row = sub_row_df.iloc[0]
                                        sub_ton_cu = int(sub_row["So_luong"])
                                        sub_ton_moi = sub_ton_cu + sub_sl_tang
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
                                        sub_log_moi = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - ➕ Nhận từ xé lẻ Combo '{selected_cb_ma}': +{sub_sl_tang} {sub_dv_con}"
                                        supabase.table("Ton_kho").upsert({
                                            "Ma_LK": sub_m,
                                            "Ten_LK": sub_name_con,
                                            "So_luong": sub_sl_tang,
                                            "Don_vi": sub_dv_con,
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
    # 7. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO (Tự động trừ định mức linh kiện/vật tư con)")
        st.markdown("---")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not combo_df.empty:
                col_ex_sc1, col_ex_sc2 = st.columns([2, 2])
                with col_ex_sc1:
                    barcode_export_cb = st.text_input("🪪 Quét / Nhập mã vạch (Barcode) để chọn Combo xuất", placeholder="Quét mã vạch sản phẩm...")
                target_cb_ma = None
                if barcode_export_cb.strip():
                    matched_cb_bc = combo_df[combo_df["Barcode"].str.contains(barcode_export_cb.strip(), case=False, na=False)]
                    if not matched_cb_bc.empty:
                        target_cb_ma = matched_cb_bc.iloc[0]["Ma_LK"]
                        st.success(f"✨ Đã nhận diện Combo: **{matched_cb_bc.iloc[0]['Ten_LK']}** (`{target_cb_ma}`)")
                    else:
                        st.warning("⚠️ Không tìm thấy Combo nào khớp với mã vạch này.")
                export_options = [f"{row['Ma_LK']} - {row['Ten_LK']}" for _, row in combo_df.iterrows()]
                default_cb_idx = 0
                if target_cb_ma:
                    for idx, opt in enumerate(export_options):
                        if opt.startswith(target_cb_ma):
                            default_cb_idx = idx
                            break
                selected_export_opt = st.selectbox("1️⃣ Chọn Combo cần xuất kho", export_options, index=default_cb_idx)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
                hien_thi_ten = current_item_row["Ten_LK"]
                ton_hien_tai = current_item_row["So_luong"]
                don_vi_tinh = current_item_row["Don_vi"]
                hinh_anh_cu = current_item_row["Hinh_anh"]
                thanh_phan_list = current_item_row.get("Thanh_phan", [])
                quy_cach_cb = int(current_item_row.get("Quy_cach", 1))
                st.warning(f"📦 **Combo chọn:** {hien_thi_ten} (`{selected_export_item}`) | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}** (1 Kiện = {quy_cach_cb} {don_vi_tinh})")
                if thanh_phan_list and isinstance(thanh_phan_list, list) and len(thanh_phan_list) > 0:
                    st.info("🔗 **Các linh kiện/vật tư con bên trong sẽ được trừ tự động theo định mức:**")
                    for tp in thanh_phan_list:
                        sub_m = tp.get('ma')
                        sub_name = tp.get('ten', 'Linh kiện')
                        sub_sl = tp.get('sl')
                        sub_dv = tp.get('dv', 'Cái')
                        sub_img = tp.get('img', '')
                        sub_item = df[df["Ma_LK"] == sub_m]
                        sub_stock = sub_item.iloc[0]["So_luong"] if not sub_item.empty else 0
                        st.write(f"- `{sub_m}` ({sub_name}) | Định mức trừ: **{sub_sl} {sub_dv} x SL xuất** | Tồn kho hiện tại: `{sub_stock}`")
                        if sub_img:
                            st.image(sub_img, width=60)
                with st.form("export_combo_form", clear_on_submit=True):
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        xuat_theo_kien = st.checkbox("📦 Xuất theo Kiện (Thùng)", value=False)
                        so_luong_xuat_raw = st.number_input("Số lượng xuất", min_value=1, step=1, value=1)
                    with col_ex2:
                        ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                    so_luong_xuat = so_luong_xuat_raw * quy_cach_cb if xuat_theo_kien else so_luong_xuat_raw
                    if xuat_theo_kien:
                        st.info(f"💡 Quy đổi xuất: {so_luong_xuat_raw} Kiện x {quy_cach_cb} = {so_luong_xuat} {don_vi_tinh}")
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
                                "Thanh_phan": thanh_phan_list,
                                "Quy_cach": quy_cach_cb
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
    # 8. XUẤT KHO LINH KIỆN LẺ
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
                qc = int(row.get("Quy_cach", 1))
                bc = row.get("Barcode", "")
                if not m.startswith(("CB", "CM")):
                    if m not in all_items_dict:
                        all_items_dict[m] = {"Ten_LK": t, "So_luong": sl, "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc, "Barcode": bc}
                tp_list = row.get("Thanh_phan", [])
                if tp_list and isinstance(tp_list, list):
                    for tp in tp_list:
                        sub_m = tp.get("ma")
                        sub_name = tp.get("ten", "Linh kiện")
                        sub_dv = tp.get("dv", "Cái")
                        if sub_m and not sub_m.startswith(("CB", "CM")) and sub_m not in all_items_dict:
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_match.empty:
                                all_items_dict[sub_m] = {
                                    "Ten_LK": sub_match.iloc[0]["Ten_LK"],
                                    "So_luong": sub_match.iloc[0]["So_luong"],
                                    "Don_vi": sub_match.iloc[0]["Don_vi"],
                                    "Hinh_anh": sub_match.iloc[0].get("Hinh_anh", ""),
                                    "Quy_cach": int(sub_match.iloc[0].get("Quy_cach", 1)),
                                    "Barcode": sub_match.iloc[0].get("Barcode", "")
                                }
                            else:
                                all_items_dict[sub_m] = {
                                    "Ten_LK": sub_name,
                                    "So_luong": 0,
                                    "Don_vi": sub_dv,
                                    "Hinh_anh": tp.get("img", ""),
                                    "Quy_cach": 1,
                                    "Barcode": ""
                                }
            col_ex_sc3, col_ex_sc4 = st.columns([2, 2])
            with col_ex_sc3:
                barcode_export_le = st.text_input("🪪 Quét / Nhập mã vạch (Barcode) để chọn linh kiện xuất", placeholder="Quét mã vạch sản phẩm...")
            target_le_ma = None
            if barcode_export_le.strip():
                for m, info in all_items_dict.items():
                    if info["Barcode"] and barcode_export_le.strip().lower() in info["Barcode"].lower():
                        target_le_ma = m
                        st.success(f"✨ Đã nhận diện: **{info['Ten_LK']}** (`{target_le_ma}`)")
                        break
                if not target_le_ma:
                    st.warning("⚠️ Không tìm thấy linh kiện nào khớp với mã vạch này.")
            export_options = [f"{m} - {info['Ten_LK']}" for m, info in all_items_dict.items()]
            default_le_idx = 0
            if target_le_ma:
                for idx, opt in enumerate(export_options):
                    if opt.startswith(target_le_ma):
                        default_le_idx = idx
                        break
            if export_options:
                selected_export_opt = st.selectbox("1️⃣ Chọn linh kiện / vật tư cần xuất kho", export_options, index=default_le_idx)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_info = all_items_dict[selected_export_item]
                hien_thi_ten = current_info["Ten_LK"]
                ton_hien_tai = current_info["So_luong"]
                don_vi_tinh = current_info["Don_vi"]
                hinh_anh_cu = current_info["Hinh_anh"]
                quy_cach_le_xuat = current_info["Quy_cach"]
                st.warning(f"🔩 **Linh kiện/Vật tư chọn:** {hien_thi_ten} (`{selected_export_item}`) | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}** (1 Kiện = {quy_cach_le_xuat} {don_vi_tinh})")
                with st.form("export_item_form", clear_on_submit=True):
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        xuat_kien_le = st.checkbox("📦 Xuất theo Kiện (Thùng)", value=False)
                        so_luong_xuat_raw = st.number_input("Số lượng xuất", min_value=1, step=1, value=1)
                    with col_ex2:
                        ngay_xuat = st.date_input("Ngày xuất", value=date.today())
                    so_luong_xuat = so_luong_xuat_raw * quy_cach_le_xuat if xuat_kien_le else so_luong_xuat_raw
                    if xuat_kien_le:
                        st.info(f"💡 Quy đổi xuất: {so_luong_xuat_raw} Kiện x {quy_cach_le_xuat} = {so_luong_xuat} {don_vi_tinh}")
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
                                "Thanh_phan": old_tp,
                                "Quy_cach": quy_cach_le_xuat
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
    # 9. BÁO CÁO & XUẤT EXCEL
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        st.markdown("---")
        st.info("💡 Bạn có thể tải toàn bộ dữ liệu tồn kho dưới dạng file **Excel (.xlsx)**.")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Quy_cach"]].copy()
                df_ton_kho.columns = ["Mã Sản Phẩm / Combo", "Tên Sản Phẩm", "Số Lượng Tồn Kho", "Đơn Vị Tính", "Quy Cách (SL/Kiện)"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho_Hien_Tai', index=False)
                df_nhat_ky = df[["Ma_LK", "Ten_LK", "Nhat_ky"]].copy()
                df_nhat_ky.columns = ["Mã Sản Phẩm", "Tên Sản Phẩm", "Lịch Sử Nhật Ký Chi Tiết"]
                df_nhat_ky.to_excel(writer, sheet_name='Lich_Su_Nhat_Ky', index=False)
            excel_data = output.getvalue()
            time_stamp = datetime.now().strftime("%Y%m%d_%H%M")
            col_rep1, col_rep2 = st.columns(2)
            with col_rep1:
                st.metric("Tổng số mặt hàng / Combo", len(df))
                st.metric("Tổng lượng kho", int(df["So_luong"].sum()) if "So_luong" in df else 0)
            with col_rep2:
                st.download_button(
                    label="📥 Tải Báo Cáo Kho Dạng Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"Bao_Cao_Kho_{time_stamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("Kho hiện đang trống!")
