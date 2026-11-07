import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
import io
import re
import unicodedata
# Cấu hình giao diện toàn màn hình
st.set_page_config(page_title="Quản Lý Đa Kho Cá Nhân", page_icon="📦", layout="wide")
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
# Tải dữ liệu tồn kho & tự động kiểm tra cấu trúc cột
@st.cache_data(ttl=0)
def load_data():
    try:
        response = supabase.table("Ton_kho").select("*").execute()
        df_load = pd.DataFrame(response.data)
        if not df_load.empty and "Kho_quan_ly" not in df_load.columns:
            df_load["Kho_quan_ly"] = "Kho 1"
        return df_load
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Định danh danh sách kho từ Kho 1 đến Kho 10
danh_sach_kho_mac_dinh = [f"Kho {i}" for i in range(1, 11)]
# Hàm định dạng tiền tệ chuẩn kế toán Việt Nam
def format_money(val):
    try:
        if pd.isna(val) or val == "":
            return "0"
        num = float(val)
        return f"{num:,.0f}".replace(",", ".")
    except Exception:
        return "0"
# Hàm loại bỏ dấu tiếng Việt & chuẩn hóa chuỗi để so sánh
def remove_vietnamese_accent(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return text.strip().lower()
# Hàm tự động sinh mã thông minh
def generate_code_from_name(full_name, is_combo=False, item_type="VT"):
    if not full_name or not full_name.strip():
        return ""
    clean_no_accent = unicodedata.normalize('NFD', full_name.strip())
    clean_no_accent = re.sub(r'[\u0300-\u036f]', '', clean_no_accent)
    clean_no_accent = clean_no_accent.replace('đ', 'd').replace('Đ', 'D')
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
# Widget Hướng dẫn quy tắc tạo mã
def render_code_guide():
    with st.expander("💡 HƯỚNG DẪN QUY TẮC TẠO MÃ SẢN PHẨM & COMBO"):
        st.markdown("""
        - **Mã Combo (`CB-`)**: Hệ thống tự động gom từ viết tắt của tên Combo.
        - **Mã Vật Tư (`VT-`)**: Dùng cho các vật tư tiêu hao, bu lông, ốc vít.
        - **Mã Linh Kiện (`LK-`)**: Dùng cho các linh kiện thiết bị, máy móc.
        """)
# Quản lý đăng nhập
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
if not st.session_state.logged_in:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ ĐA KHO")
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
        "📥 Nhập Combo mới", 
        "📥 Nhập Combo cũ", 
        "📥 Nhập linh kiện mới", 
        "📥 Nhập linh kiện cũ", 
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
        col_title, col_select_k = st.columns([2.5, 1.5])
        with col_select_k:
            selected_warehouse = st.selectbox(
                "🏢 Chọn kho xem tồn kho:", 
                ["🌐 Xem tất cả các kho"] + danh_sach_kho_mac_dinh,
                key="main_wh_select"
            )
        with col_title:
            st.title(f"📦 TỒN KHO HỆ THỐNG")
        st.markdown("---")
        if not df.empty:
            df_working = df.copy()
            for col_check in ["Gia_nhap", "Gia_xuat", "Barcode", "Quy_cach", "So_luong", "Kho_quan_ly"]:
                if col_check not in df_working.columns:
                    df_working[col_check] = "Kho 1" if col_check == "Kho_quan_ly" else (1 if col_check == "Quy_cach" else (0 if "Gia" in col_check or col_check == "So_luong" else ""))
            df_working["So_luong"] = pd.to_numeric(df_working["So_luong"], errors="coerce").fillna(0)
            df_working["Gia_nhap"] = pd.to_numeric(df_working["Gia_nhap"], errors="coerce").fillna(0)
            if selected_warehouse != "🌐 Xem tất cả các kho":
                df_filtered = df_working[df_working["Kho_quan_ly"] == selected_warehouse].copy()
                df_filtered["Thanh_tien"] = df_filtered["So_luong"] * df_filtered["Gia_nhap"]
                tong_gia_tri_kho = df_filtered["Thanh_tien"].sum()
                tong_so_luong = int(df_filtered["So_luong"].sum())
                col_m1, col_m2, col_m3 = st.columns([2, 2, 3])
                with col_m1:
                    st.metric(label="📊 TỔNG MẶT HÀNG TRONG KHO", value=f"{len(df_filtered)} sản phẩm")
                with col_m2:
                    st.metric(label="📦 TỔNG SỐ LƯỢNG TỒN", value=f"{format_money(tong_so_luong)} đơn vị")
                with col_m3:
                    st.metric(label="💰 TỔNG GIÁ TRỊ TỒN KHO", value=f"{format_money(tong_gia_tri_kho)} VNĐ")
                st.markdown("---")
                df_filtered["Gia_nhap_fmt"] = df_filtered["Gia_nhap"].apply(format_money)
                df_filtered["Gia_xuat_fmt"] = df_filtered["Gia_xuat"].apply(format_money)
                df_display = df_filtered[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt", "Barcode"]].copy()
                df_display.columns = ["Mã sản phẩm", "Tên sản phẩm", "Kho quản lý", "Tồn kho", "Đơn vị cơ bản", "Quy cách (SL/Kiện)", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)", "Mã vạch (Barcode)"]
                st.dataframe(df_display, use_container_width=True, height=500)
            else:
                def aggregate_stock(group):
                    ten_lk = group["Ten_LK"].iloc[0]
                    don_vi = group["Don_vi"].iloc[0]
                    quy_cach = group["Quy_cach"].iloc[0]
                    gia_nhap = group["Gia_nhap"].iloc[0]
                    gia_xuat = group["Gia_xuat"].iloc[0]
                    barcode = group["Barcode"].iloc[0]
                    tong_ton = int(group["So_luong"].sum())
                    chi_tiet_kho_list = []
                    for _, r in group.iterrows():
                        if r["So_luong"] > 0:
                            chi_tiet_kho_list.append(f"{r['Kho_quan_ly']} tồn {int(r['So_luong'])}")
                    chi_tiet_kho_str = ", ".join(chi_tiet_kho_list) if chi_tiet_kho_list else "Hết hàng ở các kho"
                    return pd.Series({
                        "Ten_LK": ten_lk,
                        "Chi_tiet_kho": chi_tiet_kho_str,
                        "Tong_ton": tong_ton,
                        "Don_vi": don_vi,
                        "Quy_cach": quy_cach,
                        "Gia_nhap": gia_nhap,
                        "Gia_xuat": gia_xuat,
                        "Barcode": barcode,
                        "Thanh_tien": tong_ton * gia_nhap
                    })
                df_grouped = df_working.groupby("Ma_LK", as_index=False).apply(aggregate_stock)
                tong_gia_tri_kho = df_grouped["Thanh_tien"].sum()
                tong_so_luong = int(df_grouped["Tong_ton"].sum())
                col_m1, col_m2, col_m3 = st.columns([2, 2, 3])
                with col_m1:
                    st.metric(label="📊 TỔNG MẶT HÀNG TỔNG CỘNG", value=f"{len(df_grouped)} sản phẩm")
                with col_m2:
                    st.metric(label="📦 TỔNG SỐ LƯỢNG TỒN (TẤT CẢ KHO)", value=f"{format_money(tong_so_luong)} đơn vị")
                with col_m3:
                    st.metric(label="💰 TỔNG GIÁ TRỊ TỒN KHO", value=f"{format_money(tong_gia_tri_kho)} VNĐ")
                st.markdown("---")
                df_grouped["Gia_nhap_fmt"] = df_grouped["Gia_nhap"].apply(format_money)
                df_grouped["Gia_xuat_fmt"] = df_grouped["Gia_xuat"].apply(format_money)
                df_display = df_grouped[["Ma_LK", "Ten_LK", "Chi_tiet_kho", "Tong_ton", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt", "Barcode"]].copy()
                df_display.columns = ["Mã sản phẩm", "Tên sản phẩm", "Chi tiết tồn từng kho", "Tổng tồn các kho", "Đơn vị cơ bản", "Quy cách (SL/Kiện)", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)", "Mã vạch (Barcode)"]
                st.dataframe(df_display, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm sản phẩm mới!")
    # 2. TRA CỨU & LỌC CHI TIẾT
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU & LỌC CHI TIẾT SẢN PHẨM")
        st.markdown("---")
        if not df.empty:
            col_sc1, col_sc2 = st.columns([2, 2])
            with col_sc1:
                barcode_search = st.text_input("Quét / Nhập mã vạch (Barcode) để tra cứu nhanh", placeholder="Nhấn vào đây rồi quét mã vạch...")
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
                ma_list = df["Ma_LK"].unique().tolist()
                default_idx = ma_list.index(target_ma_lk) if target_ma_lk in ma_list else 0
                selected_item = st.selectbox("Chọn mã linh kiện", ma_list, index=default_idx) if ma_list else None
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
                    matched_item_all = df[df["Ma_LK"] == selected_item]
                    stock_detail_str = ", ".join([f"{r['Kho_quan_ly']}: {r['So_luong']} {r['Don_vi']}" for _, r in matched_item_all.iterrows()])
                    st.write(f"**📦 Phân bổ tồn kho:** {stock_detail_str}")
                    st.write(f"**📦 Quy cách đóng gói:** 1 Kiện = {item_row.get('Quy_cach', 1)} {item_row.get('Don_vi', 'Cái')}")
                    st.write(f"**💰 Giá nhập:** {format_money(item_row.get('Gia_nhap', 0))} VNĐ")
                    st.write(f"**🏷️ Giá xuất:** {format_money(item_row.get('Gia_xuat', 0))} VNĐ")
                    st.write(f"**Mã vạch (Barcode):** `{item_row.get('Barcode', 'Chưa có')}`")
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
                            sub_bc_tp = tp.get('barcode', '')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_name and not sub_match.empty:
                                sub_name = sub_match.iloc[0]["Ten_LK"]
                            gia_str = f" | Giá: **{format_money(sub_gia)} VNĐ**" if sub_gia else ""
                            bc_str = f" | Barcode: `{sub_bc_tp}`" if sub_bc_tp else ""
                            st.write(f"- `{sub_m}` ({sub_name}) | Định mức: **{sub_sl} {sub_dv}**{gia_str}{bc_str}")
                            if sub_img:
                                if str(sub_img).startswith("http"):
                                    st.image(str(sub_img), width=80)
                                elif str(sub_img).startswith("local_file_"):
                                    st.info(f"📁 Ảnh đính kèm: {sub_img.replace('local_file_', '')}")
                                else:
                                    st.info(f"Ảnh linh kiện: {sub_img}")
                with col_info2:
                    img_url = item_row.get('Hinh_anh', '')
                    if img_url:
                        if str(img_url).startswith("http"):
                            st.image(str(img_url), caption=f"Ảnh: {item_row.get('Ten_LK', '')}", width=280)
                        elif str(img_url).startswith("local_file_"):
                            st.success(f"📁 Ảnh tải lên thiết bị: {img_url.replace('local_file_', '')}")
                            st.info("💡 (Ảnh lưu tham chiếu cục bộ trên máy khách).")
                        else:
                            st.image(str(img_url), caption=f"Ảnh: {item_row.get('Ten_LK', '')}", width=280)
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
                st.dataframe(filtered_df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)
            else:
                st.warning("Không tìm thấy dữ liệu nhật ký phù hợp.")
        else:
            st.info("Kho hiện đang trống.")
    # 3. ĐIỀU CHỈNH THÔNG TIN & GIÁ COMBO
    elif menu_choice == "✏️ Điều chỉnh thông tin & Giá Combo":
        st.title("✏️ ĐIỀU CHỈNH THÔNG TIN, GIÁ & THÀNH PHẦN COMBO")
        render_code_guide()
        st.markdown("---")
        if "selected_cb_to_edit" not in st.session_state:
            st.session_state.selected_cb_to_edit = ""
        combo_dict = {}
        if not df.empty:
            c_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            for _, r in c_df.iterrows():
                d_str = f"{r['Ma_LK']} - {r['Ten_LK']} ({r.get('Kho_quan_ly', 'Kho 1')})"
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
                    matched_load = df[df["Ma_LK"] == st.session_state.selected_cb_to_edit]
                    if not matched_load.empty:
                        row_l = matched_load.iloc[0]
                        st.session_state.edit_cb_ten = row_l.get("Ten_LK", "")
                        st.session_state.edit_cb_kho = row_l.get("Kho_quan_ly", "Kho 1")
                        st.session_state.edit_cb_dv = row_l.get("Don_vi", "Bộ")
                        st.session_state.edit_cb_qc = int(row_l.get("Quy_cach", 1))
                        st.session_state.edit_cb_bc = row_l.get("Barcode", "")
                        st.session_state.edit_cb_gn = int(row_l.get("Gia_nhap", 0)) if row_l.get("Gia_nhap") else 0
                        st.session_state.edit_cb_gx = int(row_l.get("Gia_xuat", 0)) if row_l.get("Gia_xuat") else 0
                        st.session_state.edit_cb_img = row_l.get("Hinh_anh", "")
                        tp_old_list = row_l.get("Thanh_phan", [])
                        for idx_l in range(1, 11):
                            if isinstance(tp_old_list, list) and (idx_l - 1) < len(tp_old_list):
                                item_t = tp_old_list[idx_l - 1]
                                st.session_state[f"ef_tp_{idx_l}_ten"] = item_t.get("ten", "")
                                st.session_state[f"ef_tp_{idx_l}_sl"] = int(item_t.get("sl", 1))
                                st.session_state[f"ef_tp_{idx_l}_dv"] = item_t.get("dv", "Cái")
                                st.session_state[f"ef_tp_{idx_l}_gia"] = int(item_t.get("gia", 0)) if item_t.get("gia") else 0
                                st.session_state[f"ef_tp_{idx_l}_ma"] = item_t.get("ma", "")
                                st.session_state[f"ef_tp_{idx_l}_img"] = item_t.get("img", "")
                                st.session_state[f"ef_tp_{idx_l}_bc"] = item_t.get("barcode", "")
                                st.session_state[f"ef_tp_{idx_l}_mode"] = "✍️ Tự viết"
                            else:
                                st.session_state[f"ef_tp_{idx_l}_ten"] = ""
                                st.session_state[f"ef_tp_{idx_l}_sl"] = 1
                                st.session_state[f"ef_tp_{idx_l}_dv"] = "Cái"
                                st.session_state[f"ef_tp_{idx_l}_gia"] = 0
                                st.session_state[f"ef_tp_{idx_l}_ma"] = ""
                                st.session_state[f"ef_tp_{idx_l}_img"] = ""
                                st.session_state[f"ef_tp_{idx_l}_bc"] = ""
                                st.session_state[f"ef_tp_{idx_l}_mode"] = "🤖 Tự sinh"
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
        def_ten = st.session_state.get("edit_cb_ten", active_data.get("Ten_LK", ""))
        def_kho = st.session_state.get("edit_cb_kho", active_data.get("Kho_quan_ly", "Kho 1"))
        def_dv = st.session_state.get("edit_cb_dv", active_data.get("Don_vi", "Bộ"))
        def_img = st.session_state.get("edit_cb_img", active_data.get("Hinh_anh", ""))
        def_tp = active_data.get("Thanh_phan", [])
        def_gianhap = st.session_state.get("edit_cb_gn", int(active_data.get("Gia_nhap", 0)) if active_data.get("Gia_nhap") else 0)
        def_giaxuat = st.session_state.get("edit_cb_gx", int(active_data.get("Gia_xuat", 0)) if active_data.get("Gia_xuat") else 0)
        def_barcode = st.session_state.get("edit_cb_bc", active_data.get("Barcode", "") if active_data.get("Barcode") else "")
        def_quycach = st.session_state.get("edit_cb_qc", int(active_data.get("Quy_cach", 1)) if active_data.get("Quy_cach") else 1)
        if target_cb_code:
            st.info(f"Đang thao tác chỉnh sửa cho Combo: **{target_cb_code}**")
        with st.form("edit_combo_form_final"):
            c1, c2 = st.columns(2)
            with c1:
                ten_lk_e = st.text_input("Tên Combo", value=def_ten, key="edit_cb_ten")
                ma_lk_e = st.text_input("Mã Combo (Cố định)", value=def_ma, disabled=True)
                kho_idx_e = danh_sach_kho_mac_dinh.index(def_kho) if def_kho in danh_sach_kho_mac_dinh else 0
                kho_quan_ly_e = st.selectbox("🏢 Kho quản lý", danh_sach_kho_mac_dinh, index=kho_idx_e, key="edit_cb_kho")
                quy_cach_e = st.number_input("Quy cách: 1 Kiện = ? Đơn vị lẻ", min_value=1, step=1, value=def_quycach, key="edit_cb_qc")
                barcode_e = st.text_input("Mã vạch (Barcode)", value=def_barcode, key="edit_cb_bc")
            with c2:
                dv_list = ["Bộ", "Hộp", "Combo"]
                dv_idx = dv_list.index(def_dv) if def_dv in dv_list else 0
                don_vi_e = st.selectbox("Đơn vị tính cơ bản", dv_list, index=dv_idx, key="edit_cb_dv")
                gia_nhap_e = st.number_input("Giá nhập Combo (VNĐ)", min_value=0, step=1000, value=def_gianhap, format="%d", key="edit_cb_gn")
                gia_xuat_e = st.number_input("Giá xuất Combo (VNĐ)", min_value=0, step=1000, value=def_giaxuat, format="%d", key="edit_cb_gx")
                uploaded_img_edit = st.file_uploader("📁 Tải ảnh sản phẩm mới (hoặc chụp ảnh)", type=["jpg", "jpeg", "png"], key="up_img_edit_cb")
                hinh_anh_e = st.text_input("Link ảnh chi tiết (URL)", value=def_img, key="edit_cb_img")
                if uploaded_img_edit is not None:
                    hinh_anh_e = f"local_file_{uploaded_img_edit.name}"
                    st.image(uploaded_img_edit, width=120)
            ghi_chu_e = st.text_input("Ghi chú điều chỉnh", placeholder="Ví dụ: Cập nhật tăng giá bán và giá nhập mới")
            st.markdown("---")
            st.markdown("### 🧩 THÀNH PHẦN COMBO HIỆN TẠI & GIÁ CHI TIẾT")
            def get_tp_val_e(idx, field):
                session_key = f"ef_tp_{idx}_"
                if field == 'ten': session_key += 'ten'
                elif field == 'sl': session_key += 'sl'
                elif field == 'dv': session_key += 'dv'
                elif field == 'gia': session_key += 'gia'
                elif field == 'ma': session_key += 'ma'
                elif field == 'img': session_key += 'img'
                elif field == 'barcode': session_key += 'bc'
                if session_key in st.session_state:
                    return st.session_state[session_key]
                if (idx - 1) < len(def_tp) and isinstance(def_tp, list):
                    val = def_tp[idx - 1].get(field, "")
                    return val if val is not None else ("" if field in ['ten', 'ma', 'img', 'barcode'] else (1 if field == 'sl' else 0))
                return "" if field in ['ten', 'ma', 'img', 'barcode'] else (1 if field == 'sl' else 0)
            tps_input_e = []
            for i in range(1, 11):
                st.markdown(f"**Thành phần {i}**")
                ef_mode_key = f"ef_tp_{i}_mode"
                ef_type_key = f"ef_tp_{i}_type"
                if ef_mode_key not in st.session_state:
                    st.session_state[ef_mode_key] = "🤖 Tự sinh" if not get_tp_val_e(i, 'ma') else "✍️ Tự viết"
                if ef_type_key not in st.session_state:
                    st.session_state[ef_type_key] = "⚙️ Linh kiện (LK)" if str(get_tp_val_e(i, 'ma')).startswith("LK") else "🔩 Vật tư (VT)"
                sub_c1, sub_c2, sub_c_dv, sub_c_gia = st.columns([3, 1, 1, 1.5])
                with sub_c1:
                    t_name_e = st.text_input(f"Tên linh kiện {i}", value=str(get_tp_val_e(i, 'ten')), key=f"ef_tp_{i}_ten")
                with sub_c2:
                    val_sl = get_tp_val_e(i, 'sl')
                    t_sl_e = st.number_input(f"Định mức {i}", min_value=1, value=int(val_sl) if str(val_sl).isdigit() else 1, key=f"ef_tp_{i}_sl")
                with sub_c_dv:
                    old_dv_e = get_tp_val_e(i, 'dv')
                    dv_sub_list = ["Cái", "Chiếc", "Bộ", "Kg", "Mét", "Túi", "Hộp", "Cuộn"]
                    dv_s_idx_e = dv_sub_list.index(old_dv_e) if old_dv_e in dv_sub_list else 0
                    t_dv_e = st.selectbox(f"Đơn vị {i}", dv_sub_list, index=dv_s_idx_e, key=f"ef_tp_{i}_dv")
                with sub_c_gia:
                    old_gia_e = get_tp_val_e(i, 'gia')
                    val_gia = int(old_gia_e) if old_gia_e and str(old_gia_e).replace('.','',1).isdigit() else 0
                    t_gia_e = st.number_input(f"Giá linh kiện {i} (VNĐ)", min_value=0, step=1000, value=val_gia, format="%d", key=f"ef_tp_{i}_gia")
                col_e_type, col_e_mode = st.columns(2)
                with col_e_type:
                    item_cat_tp_e = st.radio(
                        f"Phân loại thành phần {i}:",
                        ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"],
                        horizontal=True,
                        key=ef_type_key
                    )
                with col_e_mode:
                    item_mode_tp_e = st.radio(
                        f"Phương thức mã thành phần {i}:",
                        ["🤖 Tự sinh", "✍️ Tự viết"],
                        horizontal=True,
                        key=ef_mode_key
                    )
                prefix_tp_e = "LK" if "LK" in item_cat_tp_e else "VT"
                auto_code_tp_e = generate_code_from_name(t_name_e, is_combo=False, item_type=prefix_tp_e)
                old_code_e = get_tp_val_e(i, 'ma')
                sub_c3, sub_c4 = st.columns([2.5, 2])
                with sub_c3:
                    if item_mode_tp_e.startswith("🤖"):
                        final_tp_code_e = st.text_input(f"Mã linh kiện {i} (Tự động từ hệ thống)", value=auto_code_tp_e, key=f"ef_tp_{i}_show_auto", disabled=True)
                    else:
                        manual_e_def = old_code_e if old_code_e else auto_code_tp_e
                        final_tp_code_e = st.text_input(f"Mã linh kiện {i} (Cá nhân tự viết)", value=str(manual_e_def), key=f"ef_tp_{i}_ma")
                with sub_c4:
                    t_barcode_e = st.text_input(f"Quét/Nhập Barcode linh kiện {i}", value=str(get_tp_val_e(i, 'barcode')), key=f"ef_tp_{i}_bc")
                sub_img_c1, sub_img_c2 = st.columns([1, 1])
                with sub_img_c1:
                    uploaded_sub_img_e = st.file_uploader(f"📁 Tải ảnh linh kiện {i}", type=["jpg", "jpeg", "png"], key=f"up_ef_tp_{i}_img")
                with sub_img_c2:
                    t_img_e = st.text_input(f"Hoặc dán Link ảnh linh kiện {i} (URL)", value=str(get_tp_val_e(i, 'img')), key=f"ef_tp_{i}_img")
                if uploaded_sub_img_e is not None:
                    t_img_e = f"local_file_{uploaded_sub_img_e.name}"
                    st.image(uploaded_sub_img_e, width=80)
                elif t_img_e and str(t_img_e).startswith("http"):
                    st.image(str(t_img_e), width=80)
                st.markdown("---")
                tps_input_e.append({
                    "ten": t_name_e,
                    "ma": final_tp_code_e,
                    "sl": int(t_sl_e),
                    "dv": t_dv_e,
                    "gia": int(t_gia_e),
                    "img": t_img_e.strip() if t_img_e else "",
                    "barcode": t_barcode_e.strip() if t_barcode_e else ""
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
                            "Kho_quan_ly": kho_quan_ly_e,
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
    # 4. NHẬP COMBO MỚI
    elif menu_choice == "📥 Nhập Combo mới":
        st.title("📦 KHAI BÁO & NHẬP MỚI COMBO SẢN PHẨM")
        render_code_guide()
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input("Tên Combo", placeholder="VD: Bộ bàn ghế gỗ lim", key="new_cb_ten")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            cb_ma_mode = st.radio("Phương thức mã Combo:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_cb_mode")
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã Combo (Tự động)", value=auto_cb_code, key="new_cb_autocode")
            else:
                ma_lk = st.text_input("Mã Combo (Tự viết)", value=auto_cb_code, key="new_cb_manualcode")
            kho_nhap_cb = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_cb_kho")
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
            uploaded_img_cb = st.file_uploader("📁 Tải ảnh sản phẩm (hoặc chụp ảnh)", type=["jpg", "jpeg", "png"], key="up_img_cb")
            hinh_anh = st.text_input("Hoặc dán Link ảnh chi tiết (URL)", key="new_cb_img")
            if uploaded_img_cb is not None:
                hinh_anh = f"local_file_{uploaded_img_cb.name}"
                st.image(uploaded_img_cb, width=120)
            uploaded_phieu_cb = st.file_uploader("📁 Tải ảnh phiếu nhập kho (hoặc chụp phiếu)", type=["jpg", "jpeg", "png"], key="up_phieu_cb")
            img_phieu_nhap_cb = st.text_input("Hoặc dán Link ảnh phiếu nhập kho (URL)", key="new_cb_phieu")
            if uploaded_phieu_cb is not None:
                img_phieu_nhap_cb = f"local_file_{uploaded_phieu_cb.name}"
                st.image(uploaded_phieu_cb, width=120)
        # KIỂM TRA TRÙNG TOÀN HỆ THỐNG (Cả Trùng Mã hoặc Trùng Tên)
        is_duplicate_cb = False
        duplicate_msg_cb = ""
        if not df.empty:
            if ma_lk:
                matched_cb_any = df[df["Ma_LK"] == ma_lk]
                if not matched_cb_any.empty:
                    is_duplicate_cb = True
                    existing_kho = ", ".join(matched_cb_any["Kho_quan_ly"].unique())
                    duplicate_msg_cb = f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã Combo `{ma_lk}` đã tồn tại trong hệ thống (tại **{existing_kho}**)."
            if not is_duplicate_cb and ten_lk.strip():
                clean_ten_moi = remove_vietnamese_accent(ten_lk)
                for _, r_exist in df.iterrows():
                    if remove_vietnamese_accent(str(r_exist.get("Ten_LK", ""))) == clean_ten_moi:
                        is_duplicate_cb = True
                        duplicate_msg_cb = f"⚠️ **CẢNH BÁO TRÙNG TÊN:** Tên sản phẩm '{ten_lk}' đã tồn tại trong hệ thống với mã `{r_exist['Ma_LK']}` (tại **{r_exist.get('Kho_quan_ly', 'Kho 1')}**)! Bạn không được phép tạo 2 mã trùng tên nhau."
                        break
        if is_duplicate_cb:
            st.error(duplicate_msg_cb)
        ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập mới lô combo đầu năm", key="new_cb_note")
        st.markdown("---")
        st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN & MÃ VẠCH TỪNG LINH KIỆN CON")
        tps_input = []
        for i in range(1, 11):
            st.markdown(f"**Thành phần {i}**")
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
            sub_c3, sub_c4 = st.columns([2.5, 2])
            with sub_c3:
                if item_mode_tp.startswith("🤖"):
                    final_tp_code = st.text_input(f"Mã linh kiện {i} (Tự động từ hệ thống)", value=auto_code_tp, key=f"tp_{i}_show_auto", disabled=True)
                else:
                    final_tp_code = st.text_input(f"Mã linh kiện {i} (Cá nhân tự viết)", key=tma_key)
            with sub_c4:
                t_barcode = st.text_input(f"Quét/Nhập Barcode linh kiện {i}", key=f"new_tp_{i}_bc")
            sub_img_c1, sub_img_c2 = st.columns([1, 1])
            with sub_img_c1:
                uploaded_sub_img = st.file_uploader(f"📁 Tải ảnh linh kiện {i}", type=["jpg", "jpeg", "png"], key=f"up_new_tp_{i}_img")
            with sub_img_c2:
                t_img = st.text_input(f"Hoặc dán Link ảnh linh kiện {i} (URL)", key=f"new_tp_{i}_img")
            if uploaded_sub_img is not None:
                t_img = f"local_file_{uploaded_sub_img.name}"
                st.image(uploaded_sub_img, width=80)
            st.markdown("---")
            tps_input.append({
                "ten": t_name,
                "ma": final_tp_code,
                "sl": int(t_sl),
                "dv": t_dv,
                "gia": int(t_gia),
                "img": t_img.strip() if t_img else "",
                "barcode": t_barcode.strip() if t_barcode else ""
            })
        danh_sach_thanh_phan = [item for item in tps_input if item["ten"] and item["ten"].strip() != ""]
        st.markdown("")
        if st.button("💾 Lưu Mới Combo vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk and not is_duplicate_cb:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho '{kho_nhap_cb}': {so_luong_thuc_te} {don_vi}"
                    if img_phieu_nhap_cb:
                        nhat_ky_str += f" | 📄 [Xem ảnh phiếu nhập]({img_phieu_nhap_cb})"
                    if ghi_chu_tay:
                        nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                    new_data = {
                        "Ma_LK": ma_lk,
                        "Ten_LK": ten_lk,
                        "Kho_quan_ly": kho_nhap_cb,
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
                    if img_phieu_nhap_cb and img_phieu_nhap_cb.startswith("http"):
                        st.image(img_phieu_nhap_cb, caption="Ảnh phiếu nhập kho", width=300)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu dữ liệu: {e}")
            else:
                st.warning("Vui lòng kiểm tra lại Mã, Tên Combo hoặc tránh trùng mã/trùng tên trên toàn hệ thống!")
    # 5. NHẬP COMBO CŨ
    elif menu_choice == "📥 Nhập Combo cũ":
        st.title("📦 NHẬP BỔ SUNG COMBO CŨ")
        render_code_guide()
        st.markdown("---")
        if "selected_cb_nhap_cu" not in st.session_state:
            st.session_state.selected_cb_nhap_cu = ""
        combo_dict_nc = {}
        if not df.empty:
            c_df_nc = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            for _, r in c_df_nc.iterrows():
                d_str = f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})"
                combo_dict_nc[d_str] = r.to_dict()
        if combo_dict_nc:
            col_nc1, col_nc2 = st.columns([3, 1])
            with col_nc1:
                chosen_cb_nc_str = st.selectbox("📂 Chọn bộ Combo cũ cần nhập thêm:", list(combo_dict_nc.keys()), key="select_cb_nc_dropdown")
            with col_nc2:
                st.write("")
                st.write("")
                if st.button("📥 Nạp dữ liệu cũ lên Form", type="secondary", key="btn_load_cb_nc"):
                    st.session_state.selected_cb_nhap_cu = chosen_cb_nc_str.split(" - ")[0]
                    matched_nc = df[df["Ma_LK"] == st.session_state.selected_cb_nhap_cu]
                    if not matched_nc.empty:
                        row_nc = matched_nc.iloc[0]
                        st.session_state.nc_ten = row_nc.get("Ten_LK", "")
                        st.session_state.nc_kho = row_nc.get("Kho_quan_ly", "Kho 1")
                        st.session_state.nc_dv = row_nc.get("Don_vi", "Bộ")
                        st.session_state.nc_qc = int(row_nc.get("Quy_cach", 1))
                        st.session_state.nc_bc = row_nc.get("Barcode", "")
                        st.session_state.nc_gn = int(row_nc.get("Gia_nhap", 0)) if row_nc.get("Gia_nhap") else 0
                        st.session_state.nc_gx = int(row_nc.get("Gia_xuat", 0)) if row_nc.get("Gia_xuat") else 0
                        st.session_state.nc_img = row_nc.get("Hinh_anh", "")
                        st.session_state.nc_tp = row_nc.get("Thanh_phan", [])
                    st.success(f"Đã nạp dữ liệu Combo `{st.session_state.selected_cb_nhap_cu}` lên form!")
                    st.rerun()
        else:
            st.warning("Chưa có mã Combo nào trong hệ thống để nhập cũ!")
        target_cb_nc_code = st.session_state.selected_cb_nhap_cu
        active_nc_data = {}
        if target_cb_nc_code and not df.empty:
            m_nc = df[df["Ma_LK"] == target_cb_nc_code]
            if not m_nc.empty:
                active_nc_data = m_nc.iloc[0].to_dict()
        def_nc_ten = st.session_state.get("nc_ten", active_nc_data.get("Ten_LK", ""))
        def_nc_kho = st.session_state.get("nc_kho", active_nc_data.get("Kho_quan_ly", "Kho 1"))
        def_nc_dv = st.session_state.get("nc_dv", active_nc_data.get("Don_vi", "Bộ"))
        def_nc_qc = st.session_state.get("nc_qc", int(active_nc_data.get("Quy_cach", 1)) if active_nc_data.get("Quy_cach") else 1)
        def_nc_bc = st.session_state.get("nc_bc", active_nc_data.get("Barcode", "") if active_nc_data.get("Barcode") else "")
        def_nc_gn = st.session_state.get("nc_gn", int(active_nc_data.get("Gia_nhap", 0)) if active_nc_data.get("Gia_nhap") else 0)
        def_nc_gx = st.session_state.get("nc_gx", int(active_nc_data.get("Gia_xuat", 0)) if active_nc_data.get("Gia_xuat") else 0)
        def_nc_img = st.session_state.get("nc_img", active_nc_data.get("Hinh_anh", ""))
        def_nc_tp = st.session_state.get("nc_tp", active_nc_data.get("Thanh_phan", []))
        if target_cb_nc_code:
            st.info(f"Đang nhập bổ sung cho Combo: **{target_cb_nc_code}** ({def_nc_ten})")
        with st.form("nhap_combo_cu_form"):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Tên Combo (Cố định)", value=def_nc_ten, disabled=True)
                st.text_input("Mã Combo (Cố định)", value=target_cb_nc_code, disabled=True)
                kho_idx_nc = danh_sach_kho_mac_dinh.index(def_nc_kho) if def_nc_kho in danh_sach_kho_mac_dinh else 0
                kho_nhap_cb_cu = st.selectbox("🏢 Kho nhập", danh_sach_kho_mac_dinh, index=kho_idx_nc)
                hinh_thuc_nhap_cb_cu = st.radio("Hình thức nhập kho:", ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"], horizontal=True)
                so_luong_nhap_them_cb = st.number_input("Số lượng nhập thêm", min_value=0, step=1, value=0)
                if "📦" in hinh_thuc_nhap_cb_cu:
                    so_luong_thuc_te_cb_cu = so_luong_nhap_them_cb * def_nc_qc
                    st.info(f"💡 Quy đổi: {so_luong_nhap_them_cb} Kiện x {def_nc_qc} = **{so_luong_thuc_te_cb_cu} {def_nc_dv}**")
                else:
                    so_luong_thuc_te_cb_cu = so_luong_nhap_them_cb
                    st.info(f"💡 Nhập trực tiếp: **{so_luong_thuc_te_cb_cu} {def_nc_dv}**")
            with c2:
                st.write(f"**Giá nhập hiện tại:** {format_money(def_nc_gn)} VNĐ")
                st.write(f"**Giá xuất hiện tại:** {format_money(def_nc_gx)} VNĐ")
                uploaded_phieu_cb_cu = st.file_uploader("📁 Tải ảnh phiếu nhập kho", type=["jpg", "jpeg", "png"], key="up_phieu_cb_cu")
                img_phieu_cb_cu = st.text_input("Hoặc dán Link ảnh phiếu nhập kho (URL)", key="link_phieu_cb_cu")
                if uploaded_phieu_cb_cu is not None:
                    img_phieu_cb_cu = f"local_file_{uploaded_phieu_cb_cu.name}"
                    st.image(uploaded_phieu_cb_cu, width=120)
            ghi_chu_cb_cu = st.text_input("Ghi chú nhập thêm", placeholder="Ví dụ: Nhập bổ sung lô hàng cũ")
            submit_cb_cu = st.form_submit_button("💾 Cộng dồn vào kho Combo cũ", type="primary", use_container_width=True)
            if submit_cb_cu:
                if target_cb_nc_code:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        matched_db_cb = df[(df["Ma_LK"] == target_cb_nc_code) & (df["Kho_quan_ly"] == kho_nhap_cb_cu)] if "Kho_quan_ly" in df.columns else pd.DataFrame()
                        current_ton_cb = so_luong_thuc_te_cb_cu
                        old_logs_cb = ""
                        if not matched_db_cb.empty:
                            old_row_cb = matched_db_cb.iloc[0]
                            current_ton_cb = int(old_row_cb["So_luong"]) + int(so_luong_thuc_te_cb_cu)
                            old_logs_cb = old_row_cb.get("Nhat_ky", "")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung Combo tại '{kho_nhap_cb_cu}': +{so_luong_thuc_te_cb_cu} {def_nc_dv}"
                        if img_phieu_cb_cu:
                            nhat_ky_str += f" | 📄 [Xem ảnh phiếu nhập]({img_phieu_cb_cu})"
                        if ghi_chu_cb_cu:
                            nhat_ky_str += f" | Ghi chú: {ghi_chu_cb_cu}"
                        if old_logs_cb:
                            nhat_ky_str = old_logs_cb + "\n" + nhat_ky_str
                        update_data_cb = {
                            "Ma_LK": target_cb_nc_code,
                            "Ten_LK": def_nc_ten,
                            "Kho_quan_ly": kho_nhap_cb_cu,
                            "So_luong": int(current_ton_cb),
                            "Don_vi": def_nc_dv,
                            "Nhat_ky": nhat_ky_str,
                            "Hinh_anh": def_nc_img,
                            "Thanh_phan": def_nc_tp,
                            "Gia_nhap": float(def_nc_gn),
                            "Gia_xuat": float(def_nc_gx),
                            "Barcode": def_nc_bc,
                            "Quy_cach": int(def_nc_qc)
                        }
                        supabase.table("Ton_kho").upsert(update_data_cb).execute()
                        st.success("Đã cộng dồn số lượng vào kho Combo cũ thành công!")
                        if img_phieu_cb_cu and img_phieu_cb_cu.startswith("http"):
                            st.image(img_phieu_cb_cu, caption="Ảnh phiếu nhập kho", width=300)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng bấm nút 'Nạp dữ liệu cũ lên Form' trước khi lưu!")
    # 6. NHẬP LINH KIỆN MỚI
    elif menu_choice == "📥 Nhập linh kiện mới":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        render_code_guide()
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk_moi = st.text_input("Tên linh kiện / vật tư mới", placeholder="VD: Bulong M24x90", key="new_lk_ten")
            sub_col_t, sub_col_m = st.columns(2)
            with sub_col_t:
                item_cat_nm = st.radio("Phân loại:", ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"], horizontal=True, key="new_lk_cat")
            with sub_col_m:
                item_mode_nm = st.radio("Phương thức mã:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_lk_mode")
            prefix_nm = "LK" if "LK" in item_cat_nm else "VT"
            auto_code_nm = generate_code_from_name(ten_lk_moi, is_combo=False, item_type=prefix_nm)
            if item_mode_nm.startswith("🤖"):
                ma_lk_moi = st.text_input("Mã LK / VT (Tự động từ hệ thống)", value=auto_code_nm, disabled=True, key="new_lk_autocode")
            else:
                ma_lk_moi = st.text_input("Mã LK / VT (Cá nhân tự viết)", value=auto_code_nm, key="new_lk_manualcode")
            kho_nhap_lk_moi = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_lk_kho")
            don_vi_lk_moi = st.selectbox("Đơn vị tính cơ bản", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét", "Bộ"], key="new_lk_dv")
            hinh_thuc_nhap_lk_moi = st.radio("Hình thức nhập kho:", ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"], horizontal=True, key="new_lk_hinhthuc")
            so_luong_nhap_lk_moi = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="new_lk_sl")
            if "📦" in hinh_thuc_nhap_lk_moi:
                quy_cach_lk_moi = st.number_input("Quy cách: 1 Kiện = ? Đơn vị cơ bản", min_value=1, step=1, value=1, key="new_lk_qc")
                so_luong_thuc_te_lk_moi = so_luong_nhap_lk_moi * quy_cach_lk_moi
                st.info(f"💡 Quy đổi: {so_luong_nhap_lk_moi} Kiện x {quy_cach_lk_moi} = **{so_luong_thuc_te_lk_moi} {don_vi_lk_moi}**")
            else:
                quy_cach_lk_moi = 1
                so_luong_thuc_te_lk_moi = so_luong_nhap_lk_moi
                st.info(f"💡 Nhập trực tiếp: **{so_luong_thuc_te_lk_moi} {don_vi_lk_moi}**")
            barcode_lk_moi = st.text_input("Mã vạch (Barcode)", placeholder="Quét hoặc nhập mã vạch...", key="new_lk_bc")
        with c2:
            gia_nhap_lk_moi = st.number_input("Giá nhập (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_lk_gn")
            gia_xuat_lk_moi = st.number_input("Giá xuất (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_lk_gx")
            uploaded_img_lk_moi = st.file_uploader("📁 Tải ảnh linh kiện", type=["jpg", "jpeg", "png"], key="up_new_lk_img")
            hinh_anh_lk_moi = st.text_input("Hoặc dán Link ảnh chi tiết (URL)", key="new_lk_img")
            if uploaded_img_lk_moi is not None:
                hinh_anh_lk_moi = f"local_file_{uploaded_img_lk_moi.name}"
                st.image(uploaded_img_lk_moi, width=120)
            uploaded_phieu_lk_moi = st.file_uploader("📁 Tải ảnh phiếu nhập kho", type=["jpg", "jpeg", "png"], key="up_new_lk_phieu")
            img_phieu_lk_moi = st.text_input("Hoặc dán Link ảnh phiếu nhập kho (URL)", key="new_lk_phieu")
            if uploaded_phieu_lk_moi is not None:
                img_phieu_lk_moi = f"local_file_{uploaded_phieu_lk_moi.name}"
                st.image(uploaded_phieu_lk_moi, width=120)
        # KIỂM TRA TRÙNG TOÀN HỆ THỐNG (Tránh cả trùng mã lẫn trùng tên sản phẩm)
        is_duplicate_lk = False
        duplicate_msg_lk = ""
        if not df.empty:
            if ma_lk_moi:
                matched_lk_any = df[df["Ma_LK"] == ma_lk_moi]
                if not matched_lk_any.empty:
                    is_duplicate_lk = True
                    existing_kho = ", ".join(matched_lk_any["Kho_quan_ly"].unique())
                    duplicate_msg_lk = f"⚠️ **CẢNH BÁO TRÙNG MÃ:** Mã linh kiện `{ma_lk_moi}` đã tồn tại trong hệ thống (tại **{existing_kho}**)."
            if not is_duplicate_lk and ten_lk_moi.strip():
                clean_ten_moi_lk = remove_vietnamese_accent(ten_lk_moi)
                for _, r_exist in df.iterrows():
                    if remove_vietnamese_accent(str(r_exist.get("Ten_LK", ""))) == clean_ten_moi_lk:
                        is_duplicate_lk = True
                        duplicate_msg_lk = f"⚠️ **CẢNH BÁO TRÙNG TÊN:** Tên sản phẩm '{ten_lk_moi}' đã tồn tại trong hệ thống với mã `{r_exist['Ma_LK']}` (tại **{r_exist.get('Kho_quan_ly', 'Kho 1')}**)! Bạn không được phép tạo 2 mã trùng tên nhau."
                        break
        if is_duplicate_lk:
            st.error(duplicate_msg_lk)
        ghi_chu_lk_moi = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập mới linh kiện kho", key="new_lk_note")
        st.markdown("")
        if st.button("💾 Lưu Mới Linh kiện vào Database", type="primary", use_container_width=True):
            if ma_lk_moi and ten_lk_moi and not is_duplicate_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho mới tại '{kho_nhap_lk_moi}': +{so_luong_thuc_te_lk_moi} {don_vi_lk_moi}"
                    if img_phieu_lk_moi:
                        nhat_ky_str += f" | 📄 [Xem ảnh phiếu nhập]({img_phieu_lk_moi})"
                    if ghi_chu_lk_moi:
                        nhat_ky_str += f" | Ghi chú: {ghi_chu_lk_moi}"
                    new_data_lk = {
                        "Ma_LK": ma_lk_moi,
                        "Ten_LK": ten_lk_moi,
                        "Kho_quan_ly": kho_nhap_lk_moi,
                        "So_luong": int(so_luong_thuc_te_lk_moi),
                        "Don_vi": don_vi_lk_moi,
                        "Nhat_ky": nhat_ky_str,
                        "Hinh_anh": hinh_anh_lk_moi,
                        "Thanh_phan": [],
                        "Gia_nhap": float(gia_nhap_lk_moi),
                        "Gia_xuat": float(gia_xuat_lk_moi),
                        "Barcode": barcode_lk_moi.strip(),
                        "Quy_cach": int(quy_cach_lk_moi)
                    }
                    supabase.table("Ton_kho").upsert(new_data_lk).execute()
                    st.success("Đã tạo mới linh kiện thành công vào Database!")
                    if img_phieu_lk_moi and img_phieu_lk_moi.startswith("http"):
                        st.image(img_phieu_lk_moi, caption="Ảnh phiếu nhập kho", width=300)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu dữ liệu: {e}")
            else:
                st.warning("Vui lòng điền đầy đủ Mã, Tên linh kiện hoặc tránh trùng mã/trùng tên trên toàn hệ thống!")
    # 7. NHẬP LINH KIỆN CŨ
    elif menu_choice == "📥 Nhập linh kiện cũ":
        st.title("🔩 NHẬP BỔ SUNG LINH KIỆN / VẬT TƯ CŨ")
        render_code_guide()
        st.markdown("---")
        if "selected_lk_nhap_cu" not in st.session_state:
            st.session_state.selected_lk_nhap_cu = ""
        all_items_dict = {}
        if not df.empty:
            for _, r in df.iterrows():
                m = r["Ma_LK"]
                t = r["Ten_LK"]
                kho = r["Kho_quan_ly"] if "Kho_quan_ly" in r and pd.notna(r["Kho_quan_ly"]) else "Kho 1"
                dv = r["Don_vi"]
                sl = r["So_luong"]
                img = r.get("Hinh_anh", "")
                qc = int(r.get("Quy_cach", 1)) if pd.notna(r.get("Quy_cach")) else 1
                gn = float(r.get("Gia_nhap", 0)) if pd.notna(r.get("Gia_nhap")) else 0
                gx = float(r.get("Gia_xuat", 0)) if pd.notna(r.get("Gia_xuat")) else 0
                bc = r.get("Barcode", "")
                tp = r.get("Thanh_
