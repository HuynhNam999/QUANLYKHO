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
    page_title="Quản Lý Đa Kho, Bán Hàng & Định Vị Kho", 
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
            if "Ke_kho" not in df_load.columns: df_load["Ke_kho"] = "Kệ A"
            if "Tang_kho" not in df_load.columns: df_load["Tang_kho"] = "Tầng 1"
        return df_load
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return pd.DataFrame()
df = load_data()
# Định danh danh sách mặc định
danh_sach_kho_mac_dinh = [f"Kho {i}" for i in range(1, 11)]
danh_sach_ke_mac_dinh = [f"Kệ {k}" for k in ["A", "B", "C", "D", "E", "F", "G", "H"]]
danh_sach_tang_mac_dinh = [f"Tầng {t}" for t in range(1, 6)]
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
# Quản lý đăng nhập
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
                st.session_state.username = "Nhân viên Kho 1"
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
        "🗺️ Sơ đồ kho & Định vị vị trí",
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
                    df_working[col_check] = "Kho 1" if col_check == "Kho_quan_ly" else ("Kệ A" if col_check == "Ke_kho" else ("Tầng 1" if col_check == "Tang_kho" else (1 if col_check == "Quy_cach" else 0)))
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
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Kho", "Kệ", "Tầng", "Tồn kho", "Đơn vị cơ bản", "Quy cách", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
                st.dataframe(df_display, use_container_width=True, height=500)
            else:
                df_working["Gia_nhap_fmt"] = df_working["Gia_nhap"].apply(format_money)
                df_working["Gia_xuat_fmt"] = df_working["Gia_xuat"].apply(format_money)
                df_display = df_working[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt"]].copy()
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Kho", "Kệ", "Tầng", "Tồn kho", "Đơn vị cơ bản", "Quy cách", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
                st.dataframe(df_display, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm sản phẩm mới!")
    # 2. SƠ ĐỒ KHO & ĐỊNH VỊ VỊ TRÍ (TÍNH NĂNG MỚI)
    elif menu_choice == "🗺️ Sơ đồ kho & Định vị vị trí":
        st.title("🗺️ SƠ ĐỒ LƯU KHO & ĐỊNH VỊ VỊ TRÍ HÀNG HÓA")
        st.markdown("---")
        if not df.empty:
            df_sd = df.copy()
            if "Ke_kho" not in df_sd.columns: df_sd["Ke_kho"] = "Kệ A"
            if "Tang_kho" not in df_sd.columns: df_sd["Tang_kho"] = "Tầng 1"
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                loc_kho_sd = st.selectbox("🏢 Lọc Kho:", ["🌐 Tất cả các kho"] + danh_sach_kho_mac_dinh)
            with c_f2:
                all_kes = sorted(list(set(df_sd["Ke_kho"].dropna().tolist() + danh_sach_ke_mac_dinh)))
                loc_ke_sd = st.selectbox("📍 Lọc Kệ kho:", ["🌐 Tất cả các Kệ"] + all_kes)
            with c_f3:
                all_tangs = sorted(list(set(df_sd["Tang_kho"].dropna().tolist() + danh_sach_tang_mac_dinh)))
                loc_tang_sd = st.selectbox(" étages Lọc Tầng kho:", ["🌐 Tất cả các Tầng"] + all_tangs)
            if loc_kho_sd != "🌐 Tất cả các kho":
                df_sd = df_sd[df_sd["Kho_quan_ly"] == loc_kho_sd]
            if loc_ke_sd != "🌐 Tất cả các Kệ":
                df_sd = df_sd[df_sd["Ke_kho"] == loc_ke_sd]
            if loc_tang_sd != "🌐 Tất cả các Tầng":
                df_sd = df_sd[df_sd["Tang_kho"] == loc_tang_sd]
            st.markdown(f"### 📍 Danh sách sản phẩm nằm tại vị trí đã lọc ({len(df_sd)} mặt hàng)")
            if not df_sd.empty:
                df_sd_disp = df_sd[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi"]].copy()
                df_sd_disp.columns = ["Mã QR", "Tên sản phẩm", "Kho quản lý", "Kệ kho", "Tầng kho", "Số lượng tồn", "Đơn vị tính"]
                st.dataframe(df_sd_disp, use_container_width=True, height=450)
            else:
                st.warning("⚠️ Không có sản phẩm nào ở vị trí Kệ/Tầng này.")
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
                ke = r.get("Ke_kho", "Kệ A")
                tang = r.get("Tang_kho", "Tầng 1")
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
- 🏢 **Vị trí lưu kho:** **{target_item_info.get('Kho_quan_ly', 'Kho 1')} ➔ {target_item_info.get('Ke_kho', 'Kệ A')} ➔ {target_item_info.get('Tang_kho', 'Tầng 1')}**
- 📦 **Số lượng tồn kho:** **{target_item_info.get('So_luong', 0)} {target_item_info.get('Don_vi', 'Cái')}**
- 💰 **Giá nhập:** **{format_money(target_item_info.get('Gia_nhap', 0))} VNĐ** | 🏷️ **Giá xuất:** **{format_money(target_item_info.get('Gia_xuat', 0))} VNĐ**
                    """)
                with col_info_qr:
                    qr_bytes = generate_qr_image(str(target_item_info.get('Ma_LK', '')))
                    st.image(qr_bytes, width=160)
    # 4. ĐIỀU CHỈNH THÔNG TIN, GIÁ & VỊ TRÍ KHO
    elif menu_choice == "✏️ Điều chỉnh thông tin & Vị trí":
        st.title("✏️ ĐIỀU CHỈNH THÔNG TIN, GIÁ & VỊ TRÍ (KỆ / TẦNG)")
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
                    ke_def = selected_edit_item.get("Ke_kho", "Kệ A")
                    ke_e = st.selectbox("📍 Vị trí Kệ kho", danh_sach_ke_mac_dinh, index=danh_sach_ke_mac_dinh.index(ke_def) if ke_def in danh_sach_ke_mac_dinh else 0)
                    tang_def = selected_edit_item.get("Tang_kho", "Tầng 1")
                    tang_e = st.selectbox(" étages Vị trí Tầng kho", danh_sach_tang_mac_dinh, index=danh_sach_tang_mac_dinh.index(tang_def) if tang_def in danh_sach_tang_mac_dinh else 0)
                with c2:
                    gn_e = st.number_input("Giá nhập (VNĐ)", min_value=0, value=int(selected_edit_item.get("Gia_nhap", 0)))
                    gx_e = st.number_input("Giá xuất (VNĐ)", min_value=0, value=int(selected_edit_item.get("Gia_xuat", 0)))
                    sl_e = st.number_input("Điều chỉnh số lượng tồn", min_value=0, value=int(selected_edit_item.get("So_luong", 0)))
                ghi_chu_e = st.text_input("Ghi chú điều chỉnh", placeholder="Ví dụ: Đổi vị trí sang Kệ B Tầng 2")
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
    # 5. NHẬP COMBO MỚI
    elif menu_choice == "📥 Nhập Combo mới":
        st.title("📦 KHAI BÁO & NHẬP MỚI COMBO SẢN PHẨM")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk = st.text_input("Tên Combo", placeholder="VD: Bộ bàn ghế gỗ lim", key="new_cb_ten")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            ma_lk = st.text_input("Mã QR Combo", value=auto_cb_code, key="new_cb_code")
            kho_nhap_cb = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_cb_kho")
            ke_nhap_cb = st.selectbox("📍 Chọn Kệ kho", danh_sach_ke_mac_dinh, key="new_cb_ke")
            tang_nhap_cb = st.selectbox(" étages Chọn Tầng kho", danh_sach_tang_mac_dinh, key="new_cb_tang")
            don_vi = st.selectbox("Đơn vị tính cơ bản", ["Bộ", "Hộp", "Combo"], key="new_cb_dv")
            so_luong_nhap = st.number_input("Số lượng nhập", min_value=0, step=1, value=0, key="new_cb_sl")
        with c2:
            gia_nhap = st.number_input("Giá nhập Combo (VNĐ)", min_value=0, step=1000, value=0, key="new_cb_gn")
            gia_xuat = st.number_input("Giá xuất Combo (VNĐ)", min_value=0, step=1000, value=0, key="new_cb_gx")
            ghi_chu_tay = st.text_input("Ghi chú thêm", key="new_cb_note")
        if st.button("💾 Lưu Mới Combo vào Database", type="primary", use_container_width=True):
            if ma_lk and ten_lk:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho '{kho_nhap_cb}' ({ke_nhap_cb}-{tang_nhap_cb}): +{so_luong_nhap} {don_vi}"
                    new_data = {
                        "Ma_LK": ma_lk, "Ten_LK": ten_lk, "Kho_quan_ly": kho_nhap_cb,
                        "Ke_kho": ke_nhap_cb, "Tang_kho": tang_nhap_cb,
                        "So_luong": int(so_luong_nhap), "Don_vi": don_vi,
                        "Nhat_ky": nhat_ky_str, "Gia_nhap": float(gia_nhap),
                        "Gia_xuat": float(gia_xuat), "Quy_cach": 1, "Thanh_phan": []
                    }
                    supabase.table("Ton_kho").upsert(new_data).execute()
                    st.success("Đã tạo mới Combo thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    # 6. NHẬP LINH KIỆN MỚI
    elif menu_choice == "📥 Nhập linh kiện mới":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            ten_lk_moi = st.text_input("Tên linh kiện mới", key="new_lk_ten")
            auto_code_nm = generate_code_from_name(ten_lk_moi, is_combo=False)
            ma_lk_moi = st.text_input("Mã QR Linh kiện", value=auto_code_nm, key="new_lk_code")
            kho_nhap_lk_moi = st.selectbox("🏢 Chọn kho nhập", danh_sach_kho_mac_dinh, key="new_lk_kho")
            ke_nhap_lk_moi = st.selectbox("📍 Chọn Kệ kho", danh_sach_ke_mac_dinh, key="new_lk_ke")
            tang_nhap_lk_moi = st.selectbox(" étages Chọn Tầng kho", danh_sach_tang_mac_dinh, key="new_lk_tang")
            don_vi_lk_moi = st.selectbox("Đơn vị tính", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Bộ"], key="new_lk_dv")
            so_luong_nhap_lk_moi = st.number_input("Số lượng nhập", min_value=0, value=0, key="new_lk_sl")
        with c2:
            gia_nhap_lk_moi = st.number_input("Giá nhập (VNĐ)", min_value=0, value=0, key="new_lk_gn")
            gia_xuat_lk_moi = st.number_input("Giá xuất (VNĐ)", min_value=0, value=0, key="new_lk_gx")
        if st.button("💾 Lưu Mới Linh kiện vào Database", type="primary", use_container_width=True):
            if ma_lk_moi and ten_lk_moi:
                try:
                    ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                    nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                    nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập mới tại '{kho_nhap_lk_moi}' ({ke_nhap_lk_moi}-{tang_nhap_lk_moi}): +{so_luong_nhap_lk_moi} {don_vi_lk_moi}"
                    new_data_lk = {
                        "Ma_LK": ma_lk_moi, "Ten_LK": ten_lk_moi, "Kho_quan_ly": kho_nhap_lk_moi,
                        "Ke_kho": ke_nhap_lk_moi, "Tang_kho": tang_nhap_lk_moi,
                        "So_luong": int(so_luong_nhap_lk_moi), "Don_vi": don_vi_lk_moi,
                        "Nhat_ky": nhat_ky_str, "Gia_nhap": float(gia_nhap_lk_moi),
                        "Gia_xuat": float(gia_xuat_lk_moi), "Quy_cach": 1, "Thanh_phan": []
                    }
                    supabase.table("Ton_kho").upsert(new_data_lk).execute()
                    st.success("Đã tạo mới linh kiện thành công!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")
    # 7. BÁN HÀNG & IN HÓA ĐƠN (POS HIỂN THỊ CẢ KỆ TẦNG)
    elif menu_choice == "🛍️ Bán hàng & In hóa đơn (POS)":
        st.title("🛍️ MÀN HÌNH BÁN HÀNG & IN HÓA ĐƠN (POS)")
        st.markdown("---")
        if "cart" not in st.session_state: st.session_state.cart = []
        if not df.empty:
            all_sellable_items = {
                str(r["Ma_LK"]).strip(): {
                    "Ma_LK": r["Ma_LK"], "Ten_LK": r["Ten_LK"], "Kho_quan_ly": r.get("Kho_quan_ly", "Kho 1"),
                    "Ke_kho": r.get("Ke_kho", "Kệ A"), "Tang_kho": r.get("Tang_kho", "Tầng 1"),
                    "So_luong": r["So_luong"], "Don_vi": r["Don_vi"], "Gia_xuat": float(r.get("Gia_xuat", 0))
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
                            "Don_vi": item_info["Don_vi"], "Gia_xuat": item_info["Gia_xuat"], "So_luong_mua": sl_mua
                        })
                        st.success("Đã thêm!")
                        st.rerun()
            with col_pos2:
                st.subheader("🛒 Giỏ hàng")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart["Thành tiền"] = (df_cart["Gia_xuat"] * df_cart["So_luong_mua"]).apply(format_money)
                    st.dataframe(df_cart[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong_mua", "Thành tiền"]], use_container_width=True)
    # 8. BÁO CÁO & XUẤT EXCEL (BAO GỒM CỘT KỆ & TẦNG)
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        st.markdown("---")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Ke_kho", "Tang_kho", "So_luong", "Don_vi", "Quy_cach"]].copy()
                df_ton_kho.columns = ["Mã QR Sản Phẩm", "Tên Sản Phẩm", "Kho Quản Lý", "Kệ Kho", "Tầng Kho", "Số Lượng Tồn", "Đơn Vị Tính", "Quy Cách"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho_Hien_Tai', index=False)
            st.download_button(
                label="📥 Tải xuống file Excel tồn kho (Có Kệ & Tầng)",
                data=output.getvalue(),
                file_name=f"Bao_Cao_Ton_Kho_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
