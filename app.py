import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
import io
import re
import unicodedata
import qrcode
from PIL import Image
# Cấu hình giao diện toàn màn hình và tự động tương thích thiết bị di động
st.set_page_config(
    page_title="Quản Lý Đa Kho, Bán Hàng & Vị Trí Kệ/Mâm", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="auto"
)
# CSS căn giữa bảng, tối ưu nút bấm và giao diện trên điện thoại di động
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
    div.stButton > button {
        width: 100%;
        min-height: 2.8em;
        font-weight: bold;
    }
    .invoice-box {
        border: 1px solid #ddd;
        padding: 20px;
        background-color: #f9f9f9;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    @media (max-width: 768px) {
        .row-widget.stHorizontal {
            flex-direction: column;
        }
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
        if not df_load.empty:
            if "Kho_quan_ly" not in df_load.columns: df_load["Kho_quan_ly"] = "Kho 1"
            if "Ke_kho" not in df_load.columns: df_load["Ke_kho"] = "Kệ 1"
            if "Tang_kho" not in df_load.columns: df_load["Tang_kho"] = "Mâm 1"
        return df_load
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Danh sách lựa chọn mặc định
danh_sach_kho_mac_dinh = [f"Kho {i}" for i in range(1, 11)]
danh_sach_ke_mac_dinh = [f"Kệ {k}" for k in range(1, 11)]
danh_sach_mam_mac_dinh = [f"Mâm {m}" for m in range(1, 7)]
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
# Hàm tạo ảnh QR Code từ một chuỗi văn bản/mã sản phẩm
def generate_qr_image(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()
# Quản lý đăng nhập (Đa tài khoản & Mật khẩu riêng phân quyền)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
if not st.session_state.logged_in:
    st.title("🔐 ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ ĐA KHO & BÁN HÀNG")
    with st.form("login_form"):
        username_input = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submit_btn = st.form_submit_button("Đăng nhập")
        if submit_btn:
            if username_input == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.session_state.username = "Quản trị viên (Admin)"
                st.rerun()
            elif username_input in ["nhanvien1_an", "nv1"] and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.session_state.username = "Nhân viên An (Kho 1)"
                st.rerun()
            elif username_input in ["nhanvien1_binh", "nv1_phu"] and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.session_state.username = "Nhân viên Bình (Kho 1)"
                st.rerun()
            elif username_input == "nv_kho2" and password == "123456":
                st.session_state.logged_in = True
                st.session_state.role = "Nhân viên"
                st.session_state.username = "Nhân viên Kho 2"
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()
# --- MENU ĐIỀU HƯỚNG BÊN TRÁI ---
st.sidebar.title(f"👤 Xin chào: {st.session_state.username}")
st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Danh Mục Quản Lý")
menu_choice = st.sidebar.radio(
    "Chọn chức năng:",
    [
        "📊 Tổng quan tồn kho", 
        "🗺️ Sơ đồ kho & Vị trí Kệ / Mâm",
        "🔍 Tra cứu & Lọc chi tiết", 
        "✏️ Điều chỉnh thông tin & Vị trí",
        "📥 Nhập Combo mới", 
        "📥 Nhập Combo cũ", 
        "📥 Nhập linh kiện mới", 
        "📥 Nhập linh kiện cũ", 
        "🔄 Xé lẻ Combo thành Linh kiện", 
        "📤 Xuất kho Combo", 
        "📤 Xuất kho Linh kiện lẻ",
        "🛍️ Bán hàng & In hóa đơn (POS)",
        "📊 Báo cáo Doanh thu & Lợi nhuận",
        "📝 Quản lý Công nợ",
        "⚠️ Cảnh báo tồn kho",
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
            for col_check in ["Gia_nhap", "Gia_xuat", "Quy_cach", "So_luong", "Kho_quan_ly", "Ke_kho", "Tang_kho"]:
                if col_check not in df_working.columns:
                    df_working[col_check] = "Kho 1" if col_check == "Kho_quan_ly" else ("Kệ 1" if col_check == "Ke_kho" else ("Mâm 1" if col_check == "Tang_kho" else (1 if col_check == "Quy_cach" else 0)))
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
                df_display = df_filtered[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt"]].copy()
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Kho", "Vị trí Kệ", "Vị trí Mâm", "Tồn kho", "Đơn vị cơ bản", "Quy cách", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
                st.dataframe(df_display, use_container_width=True, height=500)
            else:
                def aggregate_stock(group):
                    ten_lk = group["Ten_LK"].iloc[0]
                    don_vi = group["Don_vi"].iloc[0]
                    quy_cach = group["Quy_cach"].iloc[0]
                    gia_nhap = group["Gia_nhap"].iloc[0]
                    gia_xuat = group["Gia_xuat"].iloc[0]
                    tong_ton = int(group["So_luong"].sum())
                    chi_tiet_kho_list = []
                    for _, r in group.iterrows():
                        if r["So_luong"] > 0:
                            chi_tiet_kho_list.append(f"{r['Kho_quan_ly']} ({r.get('Ke_kho','Kệ 1')}-{r.get('Tang_kho','Mâm 1')}) tồn {int(r['So_luong'])}")
                    chi_tiet_kho_str = ", ".join(chi_tiet_kho_list) if chi_tiet_kho_list else "Hết hàng"
                    return pd.Series({
                        "Ten_LK": ten_lk, "Chi_tiet_kho": chi_tiet_kho_str, "Tong_ton": tong_ton,
                        "Don_vi": don_vi, "Quy_cach": quy_cach, "Gia_nhap": gia_nhap, "Gia_xuat": gia_xuat,
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
                df_display = df_grouped[["Ma_LK", "Ten_LK", "Chi_tiet_kho", "Tong_ton", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt"]].copy()
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Chi tiết tồn từng kho & vị trí", "Tổng tồn", "Đơn vị", "Quy cách", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
                st.dataframe(df_display, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm sản phẩm mới!")
    # 2. SƠ ĐỒ KHO & VỊ TRÍ KỆ / MÂM
    elif menu_choice == "🗺️ Sơ đồ kho & Vị trí Kệ / Mâm":
        st.title("🗺️ SƠ ĐỒ LƯU KHO & TRA CỨU VỊ TRÍ KỆ / MÂM")
        st.markdown("---")
        if not df.empty:
            df_sd = df.copy()
            if "Ke_kho" not in df_sd.columns: df_sd["Ke_kho"] = "Kệ 1"
            if "Tang_kho" not in df_sd.columns: df_sd["Tang_kho"] = "Mâm 1"
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                loc_kho_sd = st.selectbox("🏢 Lọc Kho:", ["🌐 Tất cả các kho"] + danh_sach_kho_mac_dinh)
            with c_f2:
                all_kes = sorted(list(set(df_sd["Ke_kho"].dropna().tolist() + danh_sach_ke_mac_dinh)))
                loc_ke_sd = st.selectbox("📌 Lọc Kệ kho:", ["🌐 Tất cả các Kệ"] + all_kes)
            with c_f3:
                all_mams = sorted(list(set(df_sd["Tang_kho"].dropna().tolist() + danh_sach_mam_mac_dinh)))
                loc_tang_sd = st.selectbox("🗄️ Lọc Mâm kệ:", ["🌐 Tất cả các Mâm"] + all_mams)
            if loc_kho_sd != "🌐 Tất cả các kho":
                df_sd = df_sd[df_sd["Kho_quan_ly"] == loc_kho_sd]
            if loc_ke_sd != "🌐 Tất cả các Kệ":
                df_sd = df_sd[df_sd["Ke_kho"] == loc_ke_sd]
            if loc_tang_sd != "🌐 Tất cả các Mâm":
                df_sd = df_sd[df_sd["Tang_kho"] == loc_tang_sd]
            st.markdown(f"### 📍 Danh sách sản phẩm nằm tại vị trí đã lọc ({len(df_sd)} mặt hàng)")
            if not df_sd.empty:
                df_sd_disp = df_sd[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi"]].copy()
                df_sd_disp.columns = ["Mã QR", "Tên sản phẩm", "Kho quản lý", "Vị trí Kệ", "Vị trí Mâm", "Số lượng tồn", "Đơn vị tính"]
                st.dataframe(df_sd_disp, use_container_width=True, height=450)
            else:
                st.warning("⚠️ Không có sản phẩm nào ở vị trí Kệ / Mâm này.")
        else:
            st.info("Kho đang trống.")
    # 3. TRA CỨU & LỌC CHI TIẾT
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU, LỌC CHI TIẾT & QUÉT MÃ QR")
        st.markdown("---")
        if not df.empty:
            all_linh_kien_dict = {}
            combo_dict_tc = {}
            for _, r in df.iterrows():
                m = str(r["Ma_LK"]).strip()
                t = r["Ten_LK"]
                kho = r.get("Kho_quan_ly", "Kho 1")
                ke = r.get("Ke_kho", "Kệ 1")
                tang = r.get("Tang_kho", "Mâm 1")
                dv = r["Don_vi"]
                sl = r["So_luong"]
                img = r.get("Hinh_anh", "")
                qc = int(r.get("Quy_cach", 1))
                gn = float(r.get("Gia_nhap", 0))
                gx = float(r.get("Gia_xuat", 0))
                tp = r.get("Thanh_phan", [])
                if m.startswith(("CB", "CM")):
                    combo_dict_tc[m] = {
                        "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, "Ke_kho": ke, "Tang_kho": tang, "So_luong": sl, 
                        "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc, "Gia_nhap": gn, 
                        "Gia_xuat": gx, "Thanh_phan": tp, "Loai": "Combo"
                    }
                else:
                    if m not in all_linh_kien_dict:
                        all_linh_kien_dict[m] = {
                            "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, "Ke_kho": ke, "Tang_kho": tang, "So_luong": sl, 
                            "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc, "Gia_nhap": gn, 
                            "Gia_xuat": gx, "Loai": "Linh kiện độc lập"
                        }
            chosen_search_opt = st.selectbox("📦 Chọn sản phẩm từ danh sách có sẵn:", ["-- Chọn sản phẩm --"] + [f"{m} - {info['Ten_LK']} (Kho: {info['Kho_quan_ly']} | {info['Ke_kho']} - {info['Tang_kho']})" for m, info in {**combo_dict_tc, **all_linh_kien_dict}.items()])
            manual_search_input = st.text_input("⌨️ Mã QR / Quét máy quét:", placeholder="Nhập mã...")
            final_search_code = manual_search_input.strip() if manual_search_input.strip() else (chosen_search_opt.split(" - ")[0] if chosen_search_opt and not chosen_search_opt.startswith("--") else "")
            target_item_info = combo_dict_tc.get(final_search_code) or all_linh_kien_dict.get(final_search_code)
            if target_item_info:
                st.markdown("---")
                st.markdown("### 📄 THÔNG TIN CHI TIẾT & MÃ QR SẢN PHẨM")
                col_info1, col_info_qr = st.columns([2, 1.5])
                with col_info1:
                    st.info(f"""
- 🏷️ **Tên sản phẩm:** **{target_item_info.get('Ten_LK', '')}**
- 🔑 **Mã QR:** `{target_item_info.get('Ma_LK', '')}`
- 🏢 **Vị trí lưu kho:** **{target_item_info.get('Kho_quan_ly', 'Kho 1')} ➔ {target_item_info.get('Ke_kho', 'Kệ 1')} ➔ {target_item_info.get('Tang_kho', 'Mâm 1')}**
- 📦 **Số lượng tồn kho:** **{target_item_info.get('So_luong', 0)} {target_item_info.get('Don_vi', 'Cái')}**
- 💰 **Giá nhập:** **{format_money(target_item_info.get('Gia_nhap', 0))} VNĐ** | 🏷️ **Giá xuất:** **{format_money(target_item_info.get('Gia_xuat', 0))} VNĐ**
                    """)
                with col_info_qr:
                    qr_bytes = generate_qr_image(str(target_item_info.get('Ma_LK', '')))
                    st.image(qr_bytes, width=160)
    # 4. ĐIỀU CHỈNH THÔNG TIN & VỊ TRÍ
    elif menu_choice == "✏️ Điều chỉnh thông tin & Vị trí":
        st.title("✏️ ĐIỀU CHỈNH THÔNG TIN, GIÁ & VỊ TRÍ (KỆ / MÂM)")
        st.markdown("---")
        if not df.empty:
            all_edit_dict = {f"{r['Ma_LK']} - {r['Ten_LK']} ({r.get('Kho_quan_ly', 'Kho 1')})": r.to_dict() for _, r in df.iterrows()}
            chosen_edit_str = st.selectbox("📂 Chọn sản phẩm cần điều chỉnh:", list(all_edit_dict.keys()))
            selected_edit_item = all_edit_dict[chosen_edit_str]
            with st.form("edit_item_form"):
                c1, c2 = st.columns(2)
                with c1:
                    ten_e = st.text_input("Tên sản phẩm", value=selected_edit_item.get("Ten_LK", ""))
                    ma_e = st.text_input("Mã QR (Cố định)", value=selected_edit_item.get("Ma_LK", ""), disabled=True)
                    kho_def = selected_edit_item.get("Kho_quan_ly", "Kho 1")
                    kho_e = st.selectbox("🏢 Kho quản lý", danh_sach_kho_mac_dinh, index=danh_sach_kho_mac_dinh.index(kho_def) if kho_def in danh_sach_kho_mac_dinh else 0)
                    ke_def = selected_edit_item.get("Ke_kho", "Kệ 1")
                    ke_e = st.selectbox("📌 Chọn Kệ kho", danh_sach_ke_mac_dinh, index=danh_sach_ke_mac_dinh.index(ke_def) if ke_def in danh_sach_ke_mac_dinh else 0)
                    tang_def = selected_edit_item.get("Tang_kho", "Mâm 1")
                    tang_e = st.selectbox("🗄️ Chọn Mâm kệ", danh_sach_mam_mac_dinh, index=danh_sach_mam_mac_dinh.index(tang_def) if tang_def in danh_sach_mam_mac_dinh else 0)
                with c2:
                    gn_e = st.number_input("Giá nhập (VNĐ)", min_value=0, value=int(selected_edit_item.get("Gia_nhap", 0)))
                    gx_e = st.number_input("Giá xuất (VNĐ)", min_value=0, value=int(selected_edit_item.get("Gia_xuat", 0)))
                    sl_e = st.number_input("Điều chỉnh số lượng tồn", min_value=0, value=int(selected_edit_item.get("So_luong", 0)))
                ghi_chu_e = st.text_input("Ghi chú điều chỉnh", placeholder="Ví dụ: Đổi vị trí sang Kệ 2 Mâm 3")
                submit_edit = st.form_submit_button("💾 Cập nhật Thay đổi", type="primary", use_container_width=True)
                if submit_edit:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 🔄 Cập nhật vị trí ({ke_e} - {tang_e}) & Thông tin"
                        old_logs = selected_edit_item.get("Nhat_ky", "")
                        if old_logs: nhat_ky_str = old_logs + "\n" + nhat_ky_str
                        update_data = {
                            "Ma_LK": ma_e, "Ten_LK": ten_e, "Kho_quan_ly": kho_e,
                            "Ke_kho": ke_e, "Tang_kho": tang_e, "So_luong": int(sl_e),
                            "Don_vi": selected_edit_item.get("Don_vi", "Cái"),
                            "Nhat_ky": nhat_ky_str, "Hinh_anh": selected_edit_item.get("Hinh_anh", ""),
                            "Thanh_phan": selected_edit_item.get("Thanh_phan", []),
                            "Gia_nhap": float(gn_e), "Gia_xuat": float(gx_e),
                            "Quy_cach": int(selected_edit_item.get("Quy_cach", 1))
                        }
                        supabase.table("Ton_kho").upsert(update_data).execute()
                        st.success("Cập nhật vị trí thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
    # 5. NHẬP COMBO MỚI (ĐÃ ĐẦY ĐỦ PHẦN 2 KHAI BÁO THÀNH PHẦN)
    elif menu_choice == "📥 Nhập Combo mới":
        st.title("📦 KHAI BÁO & NHẬP MỚI COMBO SẢN PHẨM")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input("Tên Combo", placeholder="VD: Bộ bàn ghế gỗ lim", key="new_cb_ten")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            cb_ma_mode = st.radio("Phương thức mã QR Combo:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_cb_mode")
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã QR Combo (Tự động)", value=auto_cb_code, key="new_cb_autocode", disabled=True)
            else:
                ma_lk = st.text_input("Mã QR Combo (Tự viết)", value=auto_cb_code, key="new_cb_manualcode")
            kho_nhap_cb = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_cb_kho")
            ke_nhap_cb = st.selectbox("📌 Chọn Kệ kho", danh_sach_ke_mac_dinh, key="new_cb_ke")
            tang_nhap_cb = st.selectbox("🗄️ Chọn Mâm kệ", danh_sach_mam_mac_dinh, key="new_cb_tang")
            don_vi = st.selectbox("Đơn vị tính cơ bản của Combo", ["Bộ", "Hộp", "Combo"], key="new_cb_dv")
            hinh_thuc_nhap_cb = st.radio("Hình thức nhập kho:", ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"], horizontal=True, key="new_cb_hinh_thuc")
            so_luong_nhap = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="new_cb_sl")
            if "📦" in hinh_thuc_nhap_cb:
                quy_cach = st.number_input("Quy cách: 1 Kiện = ? Đơn vị cơ bản", min_value=1, step=1, value=1, key="new_cb_qc")
                so_luong_thuc_te = so_luong_nhap * quy_cach
            else:
                quy_cach = 1
                so_luong_thuc_te = so_luong_nhap
        with c2:
            gia_nhap = st.number_input("Giá nhập Combo (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_cb_gn")
            gia_xuat = st.number_input("Giá xuất Combo (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_cb_gx")
            hinh_anh = st.text_input("Link ảnh chi tiết (URL)", key="new_cb_img")
            img_phieu_nhap_cb = st.text_input("Link ảnh phiếu nhập kho (URL)", key="new_cb_phieu")
        ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập mới lô combo", key="new_cb_note")
        st.markdown("---")
        st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN & MÃ QR TỪNG LINH KIỆN CON")
        tps_input = []
        for i in range(1, 11):
            st.markdown(f"**Thành phần {i}**")
            sub_c1, sub_c2, sub_c_dv, sub_c_gia = st.columns([3, 1, 1, 1.5])
            with sub_c1:
                t_name = st.text_input(f"Tên linh kiện {i}", key=f"tp_{i}_name")
            with sub_c2:
                t_sl = st.number_input(f"Định mức {i}", min_value=1, value=1, key=f"new_tp_{i}_sl")
            with sub_c_dv:
                t_dv = st.selectbox(f"Đơn vị {i}", ["Cái", "Chiếc", "Bộ", "Kg", "Mét", "Túi", "Hộp"], key=f"new_tp_{i}_dv")
            with sub_c_gia:
                t_gia = st.number_input(f"Giá LK {i} (VNĐ)", min_value=0, step=1000, value=0, format="%d", key=f"new_tp_{i}_gia")
            auto_code_tp = generate_code_from_name(t_name, is_combo=False, item_type="LK")
            final_tp_code = st.text_input(f"Mã QR linh kiện {i}", value=auto_code_tp, key=f"tp_{i}_code")
            st.markdown("---")
            tps_input.append({
                "ten": t_name, "ma": final_tp_code, "sl": int(t_sl),
                "dv": t_dv, "gia": int(t_gia), "img": ""
            })
        danh_sach_thanh_phan = [item for item in tps_input if item["ten"] and item["ten"].strip() != ""]
        if st.button("💾 Lưu Mới Combo vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho '{kho_nhap_cb}' ({ke_nhap_cb}-{tang_nhap_cb}): +{so_luong_thuc_te} {don_vi}"
                    if ghi_chu_tay: nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
                    new_data = {
                        "Ma_LK": ma_lk, "Ten_LK": ten_lk, "Kho_quan_ly": kho_nhap_cb,
                        "Ke_kho": ke_nhap_cb, "Tang_kho": tang_nhap_cb,
                        "So_luong": int(so_luong_thuc_te), "Don_vi": don_vi,
                        "Nhat_ky": nhat_ky_str, "Hinh_anh": hinh_anh,
                        "Thanh_phan": danh_sach_thanh_phan, "Gia_nhap": float(gia_nhap),
                        "Gia_xuat": float(gia_xuat), "Quy_cach": int(quy_cach)
                    }
                    supabase.table("Ton_kho").upsert(new_data).execute()
                    st.success("Đã tạo mới Combo thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    # 6. NHẬP COMBO CŨ
    elif menu_choice == "📥 Nhập Combo cũ":
        st.title("📦 NHẬP BỔ SUNG COMBO CŨ")
        st.markdown("---")
        combo_dict_nc = {f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})": r.to_dict() for _, r in df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)].iterrows()}
        if combo_dict_nc:
            chosen_cb_nc_str = st.selectbox("📂 Chọn Combo cần nhập thêm:", list(combo_dict_nc.keys()))
            selected_cb_nc = combo_dict_nc[chosen_cb_nc_str]
            with st.form("nhap_combo_cu_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Tên Combo", value=selected_cb_nc["Ten_LK"], disabled=True)
                    st.text_input("Mã QR", value=selected_cb_nc["Ma_LK"], disabled=True)
                    kho_nc = st.selectbox("🏢 Kho nhập", danh_sach_kho_mac_dinh, index=danh_sach_kho_mac_dinh.index(selected_cb_nc.get("Kho_quan_ly","Kho 1")) if selected_cb_nc.get("Kho_quan_ly","Kho 1") in danh_sach_kho_mac_dinh else 0)
                    ke_nc = st.selectbox("📌 Kệ kho", danh_sach_ke_mac_dinh, index=danh_sach_ke_mac_dinh.index(selected_cb_nc.get("Ke_kho","Kệ 1")) if selected_cb_nc.get("Ke_kho","Kệ 1") in danh_sach_ke_mac_dinh else 0)
                    tang_nc = st.selectbox("🗄️ Mâm kệ", danh_sach_mam_mac_dinh, index=danh_sach_mam_mac_dinh.index(selected_cb_nc.get("Tang_kho","Mâm 1")) if selected_cb_nc.get("Tang_kho","Mâm 1") in danh_sach_mam_mac_dinh else 0)
                    sl_them_cb = st.number_input("Số lượng nhập thêm", min_value=0, step=1, value=0)
                with c2:
                    st.write(f"**Giá hiện tại:** Nhập {format_money(selected_cb_nc['Gia_nhap'])}đ / Xuất {format_money(selected_cb_nc['Gia_xuat'])}đ")
                ghi_chu_cb_cu = st.text_input("Ghi chú")
                if st.form_submit_button("💾 Cộng dồn vào kho Combo cũ", type="primary"):
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ton_moi = int(selected_cb_nc["So_luong"]) + int(sl_them_cb)
                        old_logs = selected_cb_nc.get("Nhat_ky", "")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung: +{sl_them_cb} {selected_cb_nc['Don_vi']}"
                        if old_logs: nhat_ky_str = old_logs + "\n" + nhat_ky_str
                        update_data_cb = {
                            "Ma_LK": selected_cb_nc["Ma_LK"], "Ten_LK": selected_cb_nc["Ten_LK"],
                            "Kho_quan_ly": kho_nc, "Ke_kho": ke_nc, "Tang_kho": tang_nc,
                            "So_luong": int(ton_moi), "Don_vi": selected_cb_nc["Don_vi"],
                            "Nhat_ky": nhat_ky_str, "Hinh_anh": selected_cb_nc.get("Hinh_anh", ""),
                            "Thanh_phan": selected_cb_nc.get("Thanh_phan", []),
                            "Gia_nhap": float(selected_cb_nc["Gia_nhap"]), "Gia_xuat": float(selected_cb_nc["Gia_xuat"]),
                            "Quy_cach": int(selected_cb_nc.get("Quy_cach", 1))
                        }
                        supabase.table("Ton_kho").upsert(update_data_cb).execute()
                        st.success("Đã cộng dồn thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.warning("Chưa có mã Combo nào!")
    # 7. NHẬP LINH KIỆN MỚI (ĐÃ ĐẦY ĐỦ CÁC TRƯỜNG)
    elif menu_choice == "📥 Nhập linh kiện mới":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk_moi = st.text_input("Tên linh kiện / vật tư mới", placeholder="VD: Bulong M24", key="new_lk_ten")
            auto_code_nm = generate_code_from_name(ten_lk_moi, is_combo=False)
            item_mode_nm = st.radio("Phương thức mã QR:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_lk_mode")
            if item_mode_nm.startswith("🤖"):
                ma_lk_moi = st.text_input("Mã QR (Tự động)", value=auto_code_nm, disabled=True, key="new_lk_auto")
            else:
                ma_lk_moi = st.text_input("Mã QR (Tự viết)", value=auto_code_nm, key="new_lk_manual")
            kho_nhap_lk_moi = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_lk_kho")
            ke_nhap_lk_moi = st.selectbox("📌 Chọn Kệ kho", danh_sach_ke_mac_dinh, key="new_lk_ke")
            tang_nhap_lk_moi = st.selectbox("🗄️ Chọn Mâm kệ", danh_sach_mam_mac_dinh, key="new_lk_tang")
            don_vi_lk_moi = st.selectbox("Đơn vị tính cơ bản", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Bộ"], key="new_lk_dv")
            so_luong_nhap_lk_moi = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="new_lk_sl")
        with c2:
            gia_nhap_lk_moi = st.number_input("Giá nhập (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_lk_gn")
            gia_xuat_lk_moi = st.number_input("Giá xuất (VNĐ)", min_value=0, step=1000, value=0, format="%d", key="new_lk_gx")
            hinh_anh_lk_moi = st.text_input("Link ảnh chi tiết (URL)", key="new_lk_img")
            img_phieu_lk_moi = st.text_input("Link ảnh phiếu nhập kho (URL)", key="new_lk_phieu")
        ghi_chu_lk_moi = st.text_input("Ghi chú thêm", key="new_lk_note")
        if st.button("💾 Lưu Mới Linh kiện vào Database", type="primary", use_container_width=True):
            if ma_lk_moi and ten_lk_moi:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập mới tại '{kho_nhap_lk_moi}' ({ke_nhap_lk_moi}-{tang_nhap_lk_moi}): +{so_luong_nhap_lk_moi} {don_vi_lk_moi}"
                    if ghi_chu_lk_moi: nhat_ky_str += f" | Ghi chú: {ghi_chu_lk_moi}"
                    new_data_lk = {
                        "Ma_LK": ma_lk_moi, "Ten_LK": ten_lk_moi, "Kho_quan_ly": kho_nhap_lk_moi,
                        "Ke_kho": ke_nhap_lk_moi, "Tang_kho": tang_nhap_lk_moi,
                        "So_luong": int(so_luong_nhap_lk_moi), "Don_vi": don_vi_lk_moi,
                        "Nhat_ky": nhat_ky_str, "Hinh_anh": hinh_anh_lk_moi,
                        "Thanh_phan": [], "Gia_nhap": float(gia_nhap_lk_moi),
                        "Gia_xuat": float(gia_xuat_lk_moi), "Quy_cach": 1
                    }
                    supabase.table("Ton_kho").upsert(new_data_lk).execute()
                    st.success("Đã tạo mới linh kiện thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    # 8. NHẬP LINH KIỆN CŨ
    elif menu_choice == "📥 Nhập linh kiện cũ":
        st.title("🔩 NHẬP BỔ SUNG LINH KIỆN / VẬT TƯ CŨ")
        st.markdown("---")
        item_dict_le_cu = {f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})": r.to_dict() for _, r in df[~df["Ma_LK"].str.startswith(("CB", "CM"), na=False)].iterrows()}
        if item_dict_le_cu:
            chosen_lk_cu_str = st.selectbox("📂 Chọn linh kiện cần nhập thêm:", list(item_dict_le_cu.keys()))
            selected_lc = item_dict_le_cu[chosen_lk_cu_str]
            with st.form("nhap_linh_kien_cu_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Tên linh kiện", value=selected_lc["Ten_LK"], disabled=True)
                    st.text_input("Mã QR", value=selected_lc["Ma_LK"], disabled=True)
                    kho_lc = st.selectbox("🏢 Kho nhập", danh_sach_kho_mac_dinh, index=danh_sach_kho_mac_dinh.index(selected_lc.get("Kho_quan_ly","Kho 1")) if selected_lc.get("Kho_quan_ly","Kho 1") in danh_sach_kho_mac_dinh else 0)
                    ke_lc = st.selectbox("📌 Kệ kho", danh_sach_ke_mac_dinh, index=danh_sach_ke_mac_dinh.index(selected_lc.get("Ke_kho","Kệ 1")) if selected_lc.get("Ke_kho","Kệ 1") in danh_sach_ke_mac_dinh else 0)
                    tang_lc = st.selectbox("🗄️ Mâm kệ", danh_sach_mam_mac_dinh, index=danh_sach_mam_mac_dinh.index(selected_lc.get("Tang_kho","Mâm 1")) if selected_lc.get("Tang_kho","Mâm 1") in danh_sach_mam_mac_dinh else 0)
                    sl_them_lc = st.number_input("Số lượng nhập thêm", min_value=0, step=1, value=0)
                with c2:
                    st.write(f"**Giá hiện tại:** Nhập {format_money(selected_lc['Gia_nhap'])}đ / Xuất {format_money(selected_lc['Gia_xuat'])}đ")
                ghi_chu_lc = st.text_input("Ghi chú")
                if st.form_submit_button("💾 Cộng dồn vào kho linh kiện cũ", type="primary"):
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ton_moi = int(selected_lc["So_luong"]) + int(sl_them_lc)
                        old_logs = selected_lc.get("Nhat_ky", "")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung: +{sl_them_lc} {selected_lc['Don_vi']}"
                        if old_logs: nhat_ky_str = old_logs + "\n" + nhat_ky_str
                        update_data_lc = {
                            "Ma_LK": selected_lc["Ma_LK"], "Ten_LK": selected_lc["Ten_LK"],
                            "Kho_quan_ly": kho_lc, "Ke_kho": ke_lc, "Tang_kho": tang_lc,
                            "So_luong": int(ton_moi), "Don_vi": selected_lc["Don_vi"],
                            "Nhat_ky": nhat_ky_str, "Hinh_anh": selected_lc.get("Hinh_anh", ""),
                            "Thanh_phan": selected_lc.get("Thanh_phan", []),
                            "Gia_nhap": float(selected_lc["Gia_nhap"]), "Gia_xuat": float(selected_lc["Gia_xuat"]),
                            "Quy_cach": int(selected_lc.get("Quy_cach", 1))
                        }
                        supabase.table("Ton_kho").upsert(update_data_lc).execute()
                        st.success("Đã cộng dồn thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.warning("Chưa có linh kiện lẻ nào!")
    # 9. XÉ LẺ COMBO THÀNH LINH KIỆN
    elif menu_choice == "🔄 Xé lẻ Combo thành Linh kiện":
        st.title("🔄 XÉ LẺ COMBO THÀNH LINH KIỆN")
        st.markdown("---")
        combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
        if not combo_df.empty:
            break_options = [f"{row['Ma_LK']} - {row['Ten_LK']} (Kho: {row.get('Kho_quan_ly', 'Kho 1')} | Tồn: {row['So_luong']})" for _, row in combo_df.iterrows()]
            selected_break_opt = st.selectbox("1️⃣ Chọn bộ Combo cần xé lẻ", break_options)
            selected_cb_ma = selected_break_opt.split(" - ")[0]
            cb_row = df[df["Ma_LK"] == selected_cb_ma].iloc[0]
            st.warning(f"📦 **Combo chọn:** {cb_row['Ten_LK']} (`{selected_cb_ma}`) | Tồn: **{cb_row['So_luong']} {cb_row['Don_vi']}**")
            cb_tp = cb_row.get("Thanh_phan", [])
            if cb_tp and isinstance(cb_tp, list) and len(cb_tp) > 0:
                with st.form("break_combo_form"):
                    so_luong_xe = st.number_input("Số lượng bộ Combo muốn xé lẻ", min_value=1, max_value=max(1, int(cb_row["So_luong"])), step=1, value=1)
                    noi_dung_xe = st.text_input("Ghi chú xé lẻ")
                    if st.form_submit_button("⚡ Xác nhận thực hiện Xé lẻ"):
                        try:
                            ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            cb_ton_moi = int(cb_row["So_luong"]) - int(so_luong_xe)
                            cb_log = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 🔄 Xé lẻ: -{so_luong_xe}"
                            if cb_row.get("Nhat_ky"): cb_log = cb_row["Nhat_ky"] + "\n" + cb_log
                            supabase.table("Ton_kho").update({"So_luong": cb_ton_moi, "Nhat_ky": cb_log}).eq("Ma_LK", selected_cb_ma).execute()
                            for tp in cb_tp:
                                sub_m = str(tp.get('ma')).strip()
                                sub_sl_tang = int(tp.get('sl', 1)) * int(so_luong_xe)
                                sub_match = df[df["Ma_LK"] == sub_m]
                                if not sub_match.empty:
                                    sub_row = sub_match.iloc[0]
                                    sub_ton_moi = int(sub_row["So_luong"]) + sub_sl_tang
                                    sub_log = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - ➕ Nhận từ xé lẻ: +{sub_sl_tang}"
                                    if sub_row.get("Nhat_ky"): sub_log = sub_row["Nhat_ky"] + "\n" + sub_log
                                    supabase.table("Ton_kho").update({"So_luong": sub_ton_moi, "Nhat_ky": sub_log}).eq("Ma_LK", sub_m).execute()
                            st.success("Xé lẻ thành công!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {e}")
            else:
                st.info("Combo này chưa có khai báo linh kiện thành phần.")
        else:
            st.warning("Không có Combo nào!")
    # 10. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO")
        st.markdown("---")
        combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
        if not combo_df.empty:
            export_options = [f"{row['Ma_LK']} - {row['Ten_LK']} (Kho: {row.get('Kho_quan_ly', 'Kho 1')} | Tồn: {row['So_luong']})" for _, row in combo_df.iterrows()]
            selected_export_opt = st.selectbox("Chọn Combo xuất kho", export_options)
            selected_cb_ma = selected_export_opt.split(" - ")[0]
            cb_row = df[df["Ma_LK"] == selected_cb_ma].iloc[0]
            with st.form("export_combo_form"):
                sl_xuat = st.number_input("Số lượng xuất", min_value=1, step=1, value=1)
                noi_dung_x = st.text_input("Lý do xuất")
                if st.form_submit_button("Xác nhận Xuất Combo"):
                    try:
                        ngay_gio = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ton_moi = int(cb_row["So_luong"]) - int(sl_xuat)
                        log_str = f"[{ngay_gio}] 👤 {nguoi_thuc_hien} - 📤 Xuất kho: -{sl_xuat}"
                        if cb_row.get("Nhat_ky"): log_str = cb_row["Nhat_ky"] + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": ton_moi, "Nhat_ky": log_str}).eq("Ma_LK", selected_cb_ma).execute()
                        # Trừ định mức linh kiện con
                        tp_list = cb_row.get("Thanh_phan", [])
                        if tp_list and isinstance(tp_list, list):
                            for tp in tp_list:
                                sub_m = str(tp.get('ma')).strip()
                                sub_sl = int(tp.get('sl', 1)) * int(sl_xuat)
                                sub_match = df[df["Ma_LK"] == sub_m]
                                if not sub_match.empty:
                                    sub_row = sub_match.iloc[0]
                                    sub_ton = max(0, int(sub_row["So_luong"]) - sub_sl)
                                    sub_log = f"[{ngay_gio}] 👤 {nguoi_thuc_hien} - 📉 Trừ tự động theo Combo: -{sub_sl}"
                                    if sub_row.get("Nhat_ky"): sub_log = sub_row["Nhat_ky"] + "\n" + sub_log
                                    supabase.table("Ton_kho").update({"So_luong": sub_ton, "Nhat_ky": sub_log}).eq("Ma_LK", sub_m).execute()
                        st.success("Xuất kho thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.warning("Không có Combo nào!")
    # 11. XUẤT KHO LINH KIỆN LẺ
    elif menu_choice == "📤 Xuất kho Linh kiện lẻ":
        st.title("📤 XUẤT KHO LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        item_dict_le = {f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})": r.to_dict() for _, r in df[~df["Ma_LK"].str.startswith(("CB", "CM"), na=False)].iterrows()}
        if item_dict_le:
            selected_le_opt = st.selectbox("Chọn linh kiện xuất kho", list(item_dict_le.keys()))
            selected_le = item_dict_le[selected_le_opt]
            with st.form("export_le_form"):
                sl_xuat_le = st.number_input("Số lượng xuất", min_value=1, step=1, value=1)
                noi_dung_lx = st.text_input("Lý do xuất")
                if st.form_submit_button("Xác nhận Xuất Lẻ"):
                    try:
                        ngay_gio = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        ton_moi = int(selected_le["So_luong"]) - int(sl_xuat_le)
                        log_str = f"[{ngay_gio}] 👤 {nguoi_thuc_hien} - 📤 Xuất lẻ: -{sl_xuat_le}"
                        if selected_le.get("Nhat_ky"): log_str = selected_le["Nhat_ky"] + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": ton_moi, "Nhat_ky": log_str}).eq("Ma_LK", selected_le["Ma_LK"]).execute()
                        st.success("Xuất kho thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.warning("Không có linh kiện lẻ nào!")
    # 12. BÁN HÀNG & IN HÓA ĐƠN (POS)
    elif menu_choice == "🛍️ Bán hàng & In hóa đơn (POS)":
        st.title("🛍️ MÀN HÌNH BÁN HÀNG & IN HÓA ĐƠN (POS)")
        st.markdown("---")
        if "cart" not in st.session_state: st.session_state.cart = []
        if "last_invoice" not in st.session_state: st.session_state.last_invoice = None
        if not df.empty:
            all_sellable_items = {
                str(r["Ma_LK"]).strip(): {
                    "Ma_LK": r["Ma_LK"], "Ten_LK": r["Ten_LK"], "Kho_quan_ly": r.get("Kho_quan_ly", "Kho 1"),
                    "Ke_kho": r.get("Ke_kho", "Kệ 1"), "Tang_kho": r.get("Tang_kho", "Mâm 1"),
                    "So_luong": r["So_luong"], "Don_vi": r["Don_vi"], "Gia_xuat": float(r.get("Gia_xuat", 0)),
                    "Gia_nhap": float(r.get("Gia_nhap", 0))
                } for _, r in df.iterrows()
            }
            col_pos1, col_pos2 = st.columns([1.5, 2.5])
            with col_pos1:
                options_pos = ["-- Chọn sản phẩm --"] + [f"{m} - {info['Ten_LK']} (Vị trí: {info['Kho_quan_ly']} / {info['Ke_kho']}-{info['Tang_kho']} | Tồn: {info['So_luong']})" for m, info in all_sellable_items.items()]
                chosen_opt_pos = st.selectbox("📦 Chọn sản phẩm:", options_pos)
                scanned_code = st.text_input("⌨️ Mã sản phẩm / Bắn QR:", placeholder="Bắn máy quét...")
                final_code = scanned_code.strip() if scanned_code.strip() else (chosen_opt_pos.split(" - ")[0] if chosen_opt_pos and not chosen_opt_pos.startswith("--") else "")
                if final_code and final_code in all_sellable_items:
                    item_info = all_sellable_items[final_code]
                    st.success(f"🎯 **{item_info['Ten_LK']}**\n\n📍 Vị trí lấy hàng: **{item_info['Kho_quan_ly']} ➔ {item_info['Ke_kho']} - {item_info['Tang_kho']}**")
                    sl_mua = st.number_input("Số lượng mua", min_value=1, max_value=max(1, int(item_info['So_luong'])), step=1, value=1)
                    if st.button("➕ Thêm vào giỏ hàng", type="primary"):
                        st.session_state.cart.append({
                            "Ma_LK": final_code, "Ten_LK": item_info["Ten_LK"], "Kho_quan_ly": item_info["Kho_quan_ly"],
                            "Ke_kho": item_info["Ke_kho"], "Tang_kho": item_info["Tang_kho"],
                            "Don_vi": item_info["Don_vi"], "Gia_xuat": item_info["Gia_xuat"], 
                            "Gia_nhap": item_info["Gia_nhap"], "So_luong_mua": sl_mua
                        })
                        st.success("Đã thêm!")
                        st.rerun()
            with col_pos2:
                st.subheader("🛒 Giỏ hàng")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart["Thành tiền"] = df_cart["Gia_xuat"] * df_cart["So_luong_mua"]
                    st.dataframe(df_cart[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong_mua"]], use_container_width=True)
                    tong_tien = df_cart["Thành tiền"].sum()
                    st.markdown(f"### 💰 TỔNG TIỀN: `{format_money(tong_tien)} VNĐ`")
                    if st.button("🗑️ Xóa sạch giỏ"):
                        st.session_state.cart = []
                        st.rerun()
                    with st.form("checkout_form"):
                        ten_khach = st.text_input("Tên khách hàng")
                        sdt_khach = st.text_input("Số điện thoại")
                        hinh_thuc_tt = st.radio("Thanh toán:", ["💵 Tiền mặt", "💳 Chuyển khoản", "📝 Ghi nợ công nợ"], horizontal=True)
                        if st.form_submit_button("✅ HOÀN TẤT THANH TOÁN & IN HÓA ĐƠN", type="primary"):
                            try:
                                ngay_gio = datetime.now().strftime("%d/%m/%Y %H:%M")
                                nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                                for c_item in st.session_state.cart:
                                    m_lk = c_item["Ma_LK"]
                                    kho = c_item["Kho_quan_ly"]
                                    sl_m = c_item["So_luong_mua"]
                                    db_match = df[(df["Ma_LK"] == m_lk) & (df["Kho_quan_ly"] == kho)]
                                    if not db_match.empty:
                                        row_db = db_match.iloc[0]
                                        ton_moi = max(0, int(row_db["So_luong"]) - sl_m)
                                        log_str = f"[{ngay_gio}] 👤 {nguoi_thuc_hien} - 🛒 Bán POS cho khách '{ten_khach}': -{sl_m} | TT: {hinh_thuc_tt}"
                                        if row_db.get("Nhat_ky"): log_str = row_db["Nhat_ky"] + "\n" + log_str
                                        supabase.table("Ton_kho").update({"So_luong": ton_moi, "Nhat_ky": log_str}).eq("Ma_LK", m_lk).eq("Kho_quan_ly", kho).execute()
                                st.session_state.last_invoice = {
                                    "ma_hd": f"HD{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                    "ngay": ngay_gio, "khach": ten_khach or "Khách lẻ",
                                    "items": st.session_state.cart.copy(), "tong_tien": tong_tien
                                }
                                st.session_state.cart = []
                                st.success("Thanh toán thành công!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi: {e}")
        if st.session_state.last_invoice:
            st.markdown("---")
            st.subheader("📄 HÓA ĐƠN GẦN NHẤT")
            inv = st.session_state.last_invoice
            st.write(f"Mã: {inv['ma_hd']} | Khách: {inv['khach']} | Tổng tiền: {format_money(inv['tong_tien'])}đ")
    # 13. BÁO CÁO DOANH THU & LỢI NHUẬN
    elif menu_choice == "📊 Báo cáo Doanh thu & Lợi nhuận":
        st.title("📊 BÁO CÁO DOANH THU & LỢI NHUẬN")
        st.markdown("---")
        sales_records = []
        for _, r in df.iterrows():
            logs = str(r.get("Nhat_ky", "")).split("\n")
            for line in logs:
                if "🛒 Bán POS" in line:
                    sales_records.append({"Tên sản phẩm": r["Ten_LK"], "Doanh thu": float(r.get("Gia_xuat", 0))})
        if sales_records:
            df_sales = pd.DataFrame(sales_records)
            st.metric("💰 TỔNG DOANH THU", f"{format_money(df_sales['Doanh thu'].sum())} VNĐ")
            st.dataframe(df_sales, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu bán hàng.")
    # 14. QUẢN LÝ CÔNG NỢ
    elif menu_choice == "📝 Quản lý Công nợ":
        st.title("📝 QUẢN LÝ CÔNG NỢ KHÁCH HÀNG")
        st.markdown("---")
        debt_records = []
        for _, r in df.iterrows():
            logs = str(r.get("Nhat_ky", "")).split("\n")
            for line in logs:
                if "📝 Ghi nợ công nợ" in line or "Ghi nợ" in line:
                    debt_records.append({"Sản phẩm": r["Ten_LK"], "Giá trị": float(r.get("Gia_xuat", 0))})
        if debt_records:
            df_debts = pd.DataFrame(debt_records)
            st.error(f"Tổng nợ: {format_money(df_debts['Giá trị'].sum())} VNĐ")
            st.dataframe(df_debts, use_container_width=True)
        else:
            st.success("Không có công nợ!")
    # 15. CẢNH BÁO TỒN KHO
    elif menu_choice == "⚠️ Cảnh báo tồn kho":
        st.title("⚠️ CẢNH BÁO TỒN KHO")
        st.markdown("---")
        nguong = st.number_input("Ngưỡng tồn kho tối thiểu:", value=20)
        df_low = df[df["So_luong"] <= nguong]
        if not df_low.empty:
            st.dataframe(df_low[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi"]], use_container_width=True)
        else:
            st.success("Tồn kho ổn định!")
    # 16. BÁO CÁO & XUẤT EXCEL
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        st.markdown("---")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi", "Quy_cach"]].copy()
                df_ton_kho.columns = ["Mã QR", "Tên Sản Phẩm", "Kho", "Vị Trí Kệ", "Vị Trí Mâm", "Tồn Kho", "Đơn Vị", "Quy Cách"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho', index=False)
            st.download_button(
                label="📥 Tải xuống file Excel tồn kho",
                data=output.getvalue(),
                file_name=f"Bao_Cao_Ton_Kho_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
