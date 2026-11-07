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
    page_title="Quản Lý Đa Kho & Bán Hàng", 
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
# Hàm tạo ảnh QR Code từ một chuỗi văn bản/mã sản phẩm
def generate_qr_image(data_str):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()
# Widget Hướng dẫn quy tắc tạo mã
def render_code_guide():
    with st.expander("💡 HƯỚNG DẪN QUY TẮC TẠO MÃ QR SẢN PHẨM & COMBO"):
        st.markdown("""
        - **Mã Combo (`CB-`)**: Dùng cho bộ sản phẩm/combo.
        - **Mã Vật Tư (`VT-`)**: Dùng cho vật tư tiêu hao, bu lông, ốc vít.
        - **Mã Linh Kiện (`LK-`)**: Dùng cho linh kiện thiết bị, máy móc.
        """)
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
        "🛍️ Bán hàng (POS)",
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
    # 0. MÀN HÌNH BÁN HÀNG (POS)
    if menu_choice == "🛍️ Bán hàng (POS)":
        st.title("🛍️ MÀN HÌNH BÁN HÀNG & THANH TOÁN (POS)")
        st.markdown("---")
        if "cart" not in st.session_state:
            st.session_state.cart = []
        if not df.empty:
            # Thu thập toàn bộ sản phẩm/combo bán được
            all_sellable_items = {}
            for _, r in df.iterrows():
                m = r["Ma_LK"]
                t = r["Ten_LK"]
                kho = r.get("Kho_quan_ly", "Kho 1")
                sl = r["So_luong"]
                dv = r["Don_vi"]
                gx = float(r.get("Gia_xuat", 0))
                tp = r.get("Thanh_phan", [])
                all_sellable_items[m] = {
                    "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, 
                    "So_luong": sl, "Don_vi": dv, "Gia_xuat": gx, "Thanh_phan": tp
                }
            col_pos1, col_pos2 = st.columns([1.5, 2.5])
            with col_pos1:
                st.subheader("🔍 Chọn sản phẩm")
                scan_pos = st.text_input("📷 Quét mã QR sản phẩm bán hàng", placeholder="Quét mã QR sản phẩm...")
                selected_code_pos = None
                if scan_pos.strip():
                    clean_pos = scan_pos.strip()
                    if clean_pos in all_sellable_items:
                        selected_code_pos = clean_pos
                        st.success(f"✨ Đã nhận diện: {all_sellable_items[clean_pos]['Ten_LK']}")
                options_pos = [f"{m} - {info['Ten_LK']} (Tồn: {info['So_luong']} {info['Don_vi']} | Giá: {format_money(info['Gia_xuat'])}đ)" for m, info in all_sellable_items.items()]
                default_pos_idx = 0
                if selected_code_pos:
                    for idx, opt in enumerate(options_pos):
                        if opt.startswith(selected_code_pos):
                            default_pos_idx = idx
                            break
                chosen_opt_pos = st.selectbox("Hoặc chọn từ danh sách:", options_pos, index=default_pos_idx)
                chosen_m_pos = chosen_opt_pos.split(" - ")[0]
                item_info = all_sellable_items[chosen_m_pos]
                st.write(f"**Giá bán:** `{format_money(item_info['Gia_xuat'])} VNĐ / {item_info['Don_vi']}`")
                st.write(f"**Tồn kho hiện tại:** `{item_info['So_luong']} {item_info['Don_vi']}` (Kho: {item_info['Kho_quan_ly']})")
                sl_mua = st.number_input("Số lượng mua", min_value=1, max_value=max(1, int(item_info['So_luong'])), step=1, value=1)
                if st.button("➕ Thêm vào giỏ hàng", type="primary"):
                    # Kiểm tra xem sản phẩm đã có trong giỏ chưa
                    found_in_cart = False
                    for cart_item in st.session_state.cart:
                        if cart_item["Ma_LK"] == chosen_m_pos:
                            cart_item["So_luong_mua"] += sl_mua
                            found_in_cart = True
                            break
                    if not found_in_cart:
                        st.session_state.cart.append({
                            "Ma_LK": chosen_m_pos,
                            "Ten_LK": item_info["Ten_LK"],
                            "Kho_quan_ly": item_info["Kho_quan_ly"],
                            "Don_vi": item_info["Don_vi"],
                            "Gia_xuat": item_info["Gia_xuat"],
                            "So_luong_mua": sl_mua,
                            "Thanh_phan": item_info["Thanh_phan"]
                        })
                    st.success("Đã thêm vào giỏ hàng!")
                    st.rerun()
            with col_pos2:
                st.subheader("🛒 Giỏ hàng hiện tại")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart["Thanh_tien"] = df_cart["Gia_xuat"] * df_cart["So_luong_mua"]
                    df_display_cart = df_cart[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong_mua", "Don_vi"]].copy()
                    df_display_cart["Gia_xuat_fmt"] = df_cart["Gia_xuat"].apply(format_money)
                    df_display_cart["Thanh_tien_fmt"] = df_cart["Thanh_tien"].apply(format_money)
                    df_display_cart.columns = ["Mã QR", "Tên sản phẩm", "Kho", "SL mua", "Đơn vị", "Đơn giá (VNĐ)", "Thành tiền (VNĐ)"]
                    st.dataframe(df_display_cart, use_container_width=True)
                    tong_tien_don_hang = df_cart["Thanh_tien"].sum()
                    st.markdown(f"### 💰 TỔNG TIỀN THANH TOÁN: `{format_money(tong_tien_don_hang)} VNĐ`")
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button("🗑️ Xóa sạch giỏ hàng"):
                            st.session_state.cart = []
                            st.rerun()
                    with col_del2:
                        pass
                    st.markdown("---")
                    st.subheader("💳 Thông tin thanh toán & Khách hàng")
                    with st.form("checkout_form"):
                        ten_khach = st.text_input("Tên khách hàng / Công ty", placeholder="Ví dụ: Anh Nam - Công ty ABC")
                        sdt_khach = st.text_input("Số điện thoại", placeholder="0912345678")
                        hinh_thuc_tt = st.radio("Hình thức thanh toán:", ["💵 Tiền mặt", "💳 Chuyển khoản ngân hàng", "📝 Ghi nợ công nợ"], horizontal=True)
                        ghi_chu_don = st.text_input("Ghi chú đơn hàng", placeholder="Ví dụ: Giao hàng buổi chiều")
                        checkout_btn = st.form_submit_button("✅ HOÀN TẤT THANH TOÁN & TRỪ KHO", type="primary", use_container_width=True)
                        if checkout_btn:
                            try:
                                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                                nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                                for c_item in st.session_state.cart:
                                    m_lk = c_item["Ma_LK"]
                                    sl_mua = c_item["So_luong_mua"]
                                    kho = c_item["Kho_quan_ly"]
                                    # Lấy tồn kho hiện tại trong DB
                                    db_match = df[(df["Ma_LK"] == m_lk) & (df["Kho_quan_ly"] == kho)]
                                    if not db_match.empty:
                                        row_db = db_match.iloc[0]
                                        ton_cu = int(row_db["So_luong"])
                                        ton_moi = max(0, ton_cu - sl_mua)
                                        old_logs = row_db.get("Nhat_ky", "")
                                        log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 🛒 Bán hàng POS cho khách '{ten_khach}': -{sl_mua} {c_item['Don_vi']} | TT: {hinh_thuc_tt}"
                                        if ghi_chu_don:
                                            log_str += f" | Ghi chú: {ghi_chu_don}"
                                        if old_logs:
                                            log_str = old_logs + "\n" + log_str
                                        # Cập nhật kho sản phẩm chính
                                        supabase.table("Ton_kho").update({
                                            "So_luong": ton_moi,
                                            "Nhat_ky": log_str
                                        }).eq("Ma_LK", m_lk).eq("Kho_quan_ly", kho).execute()
                                        # Nếu là Combo, tự động trừ định mức linh kiện con
                                        tp_list = c_item.get("Thanh_phan", [])
                                        if tp_list and isinstance(tp_list, list):
                                            for tp in tp_list:
                                                sub_ma = tp.get("ma")
                                                sub_sl_tru = int(tp.get("sl", 1)) * sl_mua
                                                sub_db = df[df["Ma_LK"] == sub_ma]
                                                if not sub_db.empty:
                                                    sub_row = sub_db.iloc[0]
                                                    sub_ton_cu = int(sub_row["So_luong"])
                                                    sub_ton_moi = max(0, sub_ton_cu - sub_sl_tru)
                                                    sub_logs = sub_row.get("Nhat_ky", "")
                                                    sub_log_moi = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📉 Trừ tự động do bán Combo '{m_lk}': -{sub_sl_tru}"
                                                    if sub_logs:
                                                        sub_log_moi = sub_logs + "\n" + sub_log_moi
                                                    supabase.table("Ton_kho").update({
                                                        "So_luong": sub_ton_moi,
                                                        "Nhat_ky": sub_log_moi
                                                    }).eq("Ma_LK", sub_ma).execute()
                                st.success(f"🎉 Thanh toán đơn hàng thành công! Tổng tiền: {format_money(tong_tien_don_hang)} VNĐ. Đã tự động trừ kho.")
                                st.session_state.cart = []
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi thanh toán: {e}")
                else:
                    st.info("Giỏ hàng đang trống. Vui lòng chọn sản phẩm để thêm vào giỏ.")
        else:
            st.info("Kho đang trống. Hãy nhập sản phẩm trước khi bán hàng.")
    # 1. TỔNG QUAN TỒN KHO
    elif menu_choice == "📊 Tổng quan tồn kho":
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
            for col_check in ["Gia_nhap", "Gia_xuat", "Quy_cach", "So_luong", "Kho_quan_ly"]:
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
                df_display = df_filtered[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt"]].copy()
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Kho quản lý", "Tồn kho", "Đơn vị cơ bản", "Quy cách (SL/Kiện)", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
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
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Chi tiết tồn từng kho", "Tổng tồn các kho", "Đơn vị cơ bản", "Quy cách (SL/Kiện)", "Giá nhập (VNĐ)", "Giá xuất (VNĐ)"]
                st.dataframe(df_display, use_container_width=True, height=500)
        else:
            st.info("Kho hiện đang trống. Hãy thêm sản phẩm mới!")
    # 2. TRA CỨU & LỌC CHI TIẾT
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU, LỌC CHI TIẾT & QUÉT MÃ QR")
        st.markdown("---")
        if not df.empty:
            all_linh_kien_dict = {}
            combo_dict_tc = {}
            for _, r in df.iterrows():
                m = r["Ma_LK"]
                t = r["Ten_LK"]
                kho = r.get("Kho_quan_ly", "Kho 1")
                dv = r["Don_vi"]
                sl = r["So_luong"]
                img = r.get("Hinh_anh", "")
                qc = int(r.get("Quy_cach", 1))
                gn = float(r.get("Gia_nhap", 0))
                gx = float(r.get("Gia_xuat", 0))
                tp = r.get("Thanh_phan", [])
                if m.startswith(("CB", "CM")):
                    combo_dict_tc[m] = {
                        "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, "So_luong": sl, 
                        "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc, "Gia_nhap": gn, 
                        "Gia_xuat": gx, "Thanh_phan": tp, "Loai": "Combo"
                    }
                else:
                    if m not in all_linh_kien_dict:
                        all_linh_kien_dict[m] = {
                            "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, "So_luong": sl, 
                            "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc, "Gia_nhap": gn, 
                            "Gia_xuat": gx, "Loai": "Linh kiện độc lập", "Thuoc_combo": []
                        }
                    all_linh_kien_dict[m]["Thuoc_combo"].append("Kho độc lập")
                if tp and isinstance(tp, list):
                    for sub in tp:
                        sub_m = sub.get("ma")
                        sub_t = sub.get("ten", "Linh kiện con")
                        sub_dv = sub.get("dv", "Cái")
                        sub_gia = float(sub.get("gia", 0))
                        if sub_m:
                            if sub_m not in all_linh_kien_dict:
                                sub_match_db = df[df["Ma_LK"] == sub_m]
                                sub_sl_ton = sub_match_db.iloc[0]["So_luong"] if not sub_match_db.empty else 0
                                sub_kho_ton = sub_match_db.iloc[0].get("Kho_quan_ly", kho) if not sub_match_db.empty else kho
                                all_linh_kien_dict[sub_m] = {
                                    "Ma_LK": sub_m, "Ten_LK": sub_t, "Kho_quan_ly": sub_kho_ton, 
                                    "So_luong": sub_sl_ton, "Don_vi": sub_dv, "Hinh_anh": sub.get("img", ""), 
                                    "Quy_cach": 1, "Gia_nhap": sub_gia, "Gia_xuat": 0, 
                                    "Loai": "Linh kiện trong Combo", "Thuoc_combo": []
                                }
                            all_linh_kien_dict[sub_m]["Thuoc_combo"].append(f"Nằm trong Combo: {m} ({t})")
            col_sc1, col_sc2 = st.columns([2, 2])
            with col_sc1:
                qr_search = st.text_input("📷 Quét / Nhập mã QR để tra cứu nhanh", placeholder="Nhấn vào đây rồi quét mã QR sản phẩm...")
            target_item_info = None
            if qr_search.strip():
                clean_q = qr_search.strip()
                if clean_q in combo_dict_tc:
                    target_item_info = combo_dict_tc[clean_q]
                    st.success(f"✨ Đã nhận diện Combo qua mã QR: **{target_item_info['Ten_LK']}** (`{clean_q}`)")
                elif clean_q in all_linh_kien_dict:
                    target_item_info = all_linh_kien_dict[clean_q]
                    st.success(f"✨ Đã nhận diện Linh kiện qua mã QR: **{target_item_info['Ten_LK']}** (`{clean_q}`)")
                else:
                    st.warning("⚠️ Không tìm thấy sản phẩm nào khớp với mã QR này.")
            col_f_chon, col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2, 1.5])
            with col_f_chon:
                che_do_xem = st.radio("Loại tìm kiếm:", ["📦 Tìm Combo", "🔩 Tìm Linh kiện lẻ"], horizontal=True)
            with col_f1:
                loai_loc = st.selectbox("Hạng mục hoạt động", ["Tất cả", "📥 Nhập kho", "📤 Xuất kho", "🔄 Cập nhật thông tin"])
            with col_f2:
                if "📦" in che_do_xem:
                    cb_list = list(combo_dict_tc.keys())
                    default_cb_idx = cb_list.index(target_item_info["Ma_LK"]) if target_item_info and target_item_info["Ma_LK"] in cb_list else 0
                    selected_code = st.selectbox("Chọn mã Combo", cb_list, index=default_cb_idx) if cb_list else None
                    current_detail = combo_dict_tc.get(selected_code, {}) if selected_code else {}
                else:
                    lk_list = list(all_linh_kien_dict.keys())
                    default_lk_idx = lk_list.index(target_item_info["Ma_LK"]) if target_item_info and target_item_info["Ma_LK"] in lk_list else 0
                    selected_code = st.selectbox("Chọn mã linh kiện lẻ", lk_list, index=default_lk_idx) if lk_list else None
                    current_detail = all_linh_kien_dict.get(selected_code, {}) if selected_code else {}
            with col_f3:
                bat_tat_ngay = st.checkbox("Lọc theo ngày")
                ngay_chon = st.date_input("Chọn ngày", value=date.today())
            if current_detail:
                st.markdown("### 📄 Thông tin chi tiết & Mã QR Sản Phẩm")
                col_info1, col_info_qr = st.columns([2, 1.5])
                with col_info1:
                    st.write(f"**Mã QR:** `{current_detail.get('Ma_LK', '')}`")
                    st.write(f"**Tên sản phẩm:** {current_detail.get('Ten_LK', '')}")
                    st.write(f"**🏢 Kho quản lý:** {current_detail.get('Kho_quan_ly', 'Kho 1')}")
                    st.write(f"**📦 Tồn kho:** {current_detail.get('So_luong', 0)} {current_detail.get('Don_vi', 'Cái')}")
                    if "📦" in che_do_xem:
                        st.write(f"**Quy cách:** 1 Kiện = {current_detail.get('Quy_cach', 1)} {current_detail.get('Don_vi', 'Bộ')}")
                    st.write(f"**💰 Giá nhập:** {format_money(current_detail.get('Gia_nhap', 0))} VNĐ")
                    if current_detail.get('Gia_xuat', 0) > 0:
                        st.write(f"**🏷️ Giá xuất:** {format_money(current_detail.get('Gia_xuat', 0))} VNĐ")
                    if "🔩" in che_do_xem:
                        thuoc_cb = current_detail.get('Thuoc_combo', [])
                        st.markdown("**🔗 Phân bổ trong hệ thống:**")
                        for tc in thuoc_cb:
                            st.write(f"- {tc}")
                    tp_hien_thi = current_detail.get('Thanh_phan', [])
                    if tp_hien_thi and isinstance(tp_hien_thi, list):
                        st.markdown("**🔗 Các linh kiện thành phần trong bộ Combo:**")
                        for tp in tp_hien_thi:
                            st.write(f"- `{tp.get('ma')}` ({tp.get('ten')}) | Định mức: **{tp.get('sl')} {tp.get('dv', 'Cái')}**")
                with col_info_qr:
                    st.markdown("📱 **Mã QR Sản Phẩm:**")
                    qr_bytes = generate_qr_image(str(current_detail.get('Ma_LK', '')))
                    st.image(qr_bytes, caption=f"Mã QR: {current_detail.get('Ma_LK', '')}", width=200)
                    st.download_button(
                        label="📥 Tải ảnh QR Code",
                        data=qr_bytes,
                        file_name=f"QR_{current_detail.get('Ma_LK', 'code')}.png",
                        mime="image/png"
                    )
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
            if selected_code:
                filtered_df = filtered_df[filtered_df["Ma_LK"] == selected_code]
            if bat_tat_ngay:
                format_ngay = ngay_chon.strftime("%d/%m/%Y")
                filtered_df = filtered_df[filtered_df["Nhat_ky"].str.contains(format_ngay, na=False)]
                st.info(f"Đang lọc ngày: **{format_ngay}**")
            if not filtered_df.empty:
                st.dataframe(filtered_df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Nhat_ky"]], use_container_width=True)
            else:
                st.warning("Không tìm thấy dữ liệu nhật ký phù hợp cho sản phẩm này.")
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
                                st.session_state[f"ef_tp_{idx_l}_mode"] = "✍️ Tự viết"
                            else:
                                st.session_state[f"ef_tp_{idx_l}_ten"] = ""
                                st.session_state[f"ef_tp_{idx_l}_sl"] = 1
                                st.session_state[f"ef_tp_{idx_l}_dv"] = "Cái"
                                st.session_state[f"ef_tp_{idx_l}_gia"] = 0
                                st.session_state[f"ef_tp_{idx_l}_ma"] = ""
                                st.session_state[f"ef_tp_{idx_l}_img"] = ""
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
        def_quycach = st.session_state.get("edit_cb_qc", int(active_data.get("Quy_cach", 1)) if active_data.get("Quy_cach") else 1)
        if target_cb_code:
            st.info(f"Đang thao tác chỉnh sửa cho Combo: **{target_cb_code}**")
        with st.form("edit_combo_form_final"):
            c1, c2 = st.columns(2)
            with c1:
                ten_lk_e = st.text_input("Tên Combo", value=def_ten, key="edit_cb_ten")
                ma_lk_e = st.text_input("Mã QR Combo (Cố định)", value=def_ma, disabled=True)
                kho_idx_e = danh_sach_kho_mac_dinh.index(def_kho) if def_kho in danh_sach_kho_mac_dinh else 0
                kho_quan_ly_e = st.selectbox("🏢 Kho quản lý", danh_sach_kho_mac_dinh, index=kho_idx_e, key="edit_cb_kho")
                quy_cach_e = st.number_input("Quy cách: 1 Kiện = ? Đơn vị lẻ", min_value=1, step=1, value=def_quycach, key="edit_cb_qc")
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
                if session_key in st.session_state:
                    return st.session_state[session_key]
                if (idx - 1) < len(def_tp) and isinstance(def_tp, list):
                    val = def_tp[idx - 1].get(field, "")
                    return val if val is not None else ("" if field in ['ten', 'ma', 'img'] else (1 if field == 'sl' else 0))
                return "" if field in ['ten', 'ma', 'img'] else (1 if field == 'sl' else 0)
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
                        f"Phương thức mã QR thành phần {i}:",
                        ["🤖 Tự sinh", "✍️ Tự viết"],
                        horizontal=True,
                        key=ef_mode_key
                    )
                prefix_tp_e = "LK" if "LK" in item_cat_tp_e else "VT"
                auto_code_tp_e = generate_code_from_name(t_name_e, is_combo=False, item_type=prefix_tp_e)
                old_code_e = get_tp_val_e(i, 'ma')
                sub_c3 = st.columns([1])[0]
                with sub_c3:
                    if item_mode_tp_e.startswith("🤖"):
                        final_tp_code_e = st.text_input(f"Mã QR linh kiện {i} (Tự động)", value=auto_code_tp_e, key=f"ef_tp_{i}_show_auto", disabled=True)
                    else:
                        manual_e_def = old_code_e if old_code_e else auto_code_tp_e
                        final_tp_code_e = st.text_input(f"Mã QR linh kiện {i} (Tự viết)", value=str(manual_e_def), key=f"ef_tp_{i}_ma")
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
                            "Kho_quan_ly": kho_quan_ly_e,
                            "So_luong": int(old_row["So_luong"]),
                            "Don_vi": don_vi_e,
                            "Nhat_ky": nhat_ky_str,
                            "Hinh_anh": hinh_anh_e,
                            "Thanh_phan": danh_sach_thanh_phan_e,
                            "Gia_nhap": float(gia_nhap_e),
                            "Gia_xuat": float(gia_xuat_e),
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
            cb_ma_mode = st.radio("Phương thức mã QR Combo:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_cb_mode")
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã QR Combo (Tự động)", value=auto_cb_code, key="new_cb_autocode")
            else:
                ma_lk = st.text_input("Mã QR Combo (Tự viết)", value=auto_cb_code, key="new_cb_manualcode")
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
        # KIỂM TRA TRÙNG TOÀN HỆ THỐNG
        is_duplicate_cb = False
        duplicate_msg_cb = ""
        if not df.empty:
            if ma_lk:
                matched_cb_any = df[df["Ma_LK"] == ma_lk]
                if not matched_cb_any.empty:
                    is_duplicate_cb = True
                    existing_kho = ", ".join(matched_cb_any["Kho_quan_ly"].unique())
                    duplicate_msg_cb = f"⚠️ **CẢNH BÁO TRÙNG MÃ QR:** Mã Combo `{ma_lk}` đã tồn tại trong hệ thống (tại **{existing_kho}**)."
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
        st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN & MÃ QR TỪNG LINH KIỆN CON")
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
                    f"Phương thức mã QR thành phần {i}:",
                    ["🤖 Tự sinh", "✍️ Tự viết"],
                    horizontal=True,
                    key=tmode_key,
                    on_change=make_name_change_cb(i)
                )
            prefix_tp = "LK" if "LK" in item_cat_tp else "VT"
            auto_code_tp = generate_code_from_name(t_name, is_combo=False, item_type=prefix_tp)
            sub_c3 = st.columns([1])[0]
            with sub_c3:
                if item_mode_tp.startswith("🤖"):
                    final_tp_code = st.text_input(f"Mã QR linh kiện {i} (Tự động)", value=auto_code_tp, key=f"tp_{i}_show_auto", disabled=True)
                else:
                    final_tp_code = st.text_input(f"Mã QR linh kiện {i} (Tự viết)", key=tma_key)
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
                "img": t_img.strip() if t_img else ""
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
        col_qr_nc, col_sel_nc = st.columns([2, 2])
        with col_qr_nc:
            scan_qr_nc = st.text_input("📷 Quét mã QR Combo cần nhập thêm", placeholder="Quét mã QR sản phẩm...")
            if scan_qr_nc.strip():
                match_qr_code = scan_qr_nc.strip()
                for d_str, r_info in combo_dict_nc.items():
                    if r_info["Ma_LK"] == match_qr_code:
                        st.session_state.selected_cb_nhap_cu = match_qr_code
                        st.success(f"✨ Đã quét nhận diện Combo: `{match_qr_code}`")
                        break
        if combo_dict_nc:
            with col_sel_nc:
                combo_keys = list(combo_dict_nc.keys())
                def_cb_nc_idx = 0
                if st.session_state.selected_cb_nhap_cu:
                    for idx, k in enumerate(combo_keys):
                        if k.startswith(st.session_state.selected_cb_nhap_cu):
                            def_cb_nc_idx = idx
                            break
                chosen_cb_nc_str = st.selectbox("📂 Hoặc chọn từ danh sách:", combo_keys, index=def_cb_nc_idx, key="select_cb_nc_dropdown")
                st.session_state.selected_cb_nhap_cu = chosen_cb_nc_str.split(" - ")[0]
            matched_nc = df[df["Ma_LK"] == st.session_state.selected_cb_nhap_cu]
            if not matched_nc.empty:
                row_nc = matched_nc.iloc[0]
                def_nc_ten = row_nc.get("Ten_LK", "")
                def_nc_kho = row_nc.get("Kho_quan_ly", "Kho 1")
                def_nc_dv = row_nc.get("Don_vi", "Bộ")
                def_nc_qc = int(row_nc.get("Quy_cach", 1))
                def_nc_gn = int(row_nc.get("Gia_nhap", 0)) if row_nc.get("Gia_nhap") else 0
                def_nc_gx = int(row_nc.get("Gia_xuat", 0)) if row_nc.get("Gia_xuat") else 0
                def_nc_img = row_nc.get("Hinh_anh", "")
                def_nc_tp = row_nc.get("Thanh_phan", [])
            else:
                def_nc_ten, def_nc_kho, def_nc_dv, def_nc_qc, def_nc_gn, def_nc_gx, def_nc_img, def_nc_tp = "", "Kho 1", "Bộ", 1, 0, 0, "", []
            st.info(f"Đang nhập bổ sung cho Combo: **{st.session_state.selected_cb_nhap_cu}** ({def_nc_ten})")
            with st.form("nhap_combo_cu_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Tên Combo (Cố định)", value=def_nc_ten, disabled=True)
                    st.text_input("Mã QR Combo (Cố định)", value=st.session_state.selected_cb_nhap_cu, disabled=True)
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
                    if st.session_state.selected_cb_nhap_cu:
                        try:
                            ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            matched_db_cb = df[(df["Ma_LK"] == st.session_state.selected_cb_nhap_cu) & (df["Kho_quan_ly"] == kho_nhap_cb_cu)] if "Kho_quan_ly" in df.columns else pd.DataFrame()
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
                                "Ma_LK": st.session_state.selected_cb_nhap_cu,
                                "Ten_LK": def_nc_ten,
                                "Kho_quan_ly": kho_nhap_cb_cu,
                                "So_luong": int(current_ton_cb),
                                "Don_vi": def_nc_dv,
                                "Nhat_ky": nhat_ky_str,
                                "Hinh_anh": def_nc_img,
                                "Thanh_phan": def_nc_tp,
                                "Gia_nhap": float(def_nc_gn),
                                "Gia_xuat": float(def_nc_gx),
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
                        st.warning("Vui lòng chọn hoặc quét mã QR Combo trước khi lưu!")
        else:
            st.warning("Chưa có mã Combo nào trong hệ thống để nhập cũ!")
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
                item_mode_nm = st.radio("Phương thức mã QR:", ["🤖 Tự sinh", "✍️ Tự viết"], horizontal=True, key="new_lk_mode")
            prefix_nm = "LK" if "LK" in item_cat_nm else "VT"
            auto_code_nm = generate_code_from_name(ten_lk_moi, is_combo=False, item_type=prefix_nm)
            if item_mode_nm.startswith("🤖"):
                ma_lk_moi = st.text_input("Mã QR LK / VT (Tự động từ hệ thống)", value=auto_code_nm, disabled=True, key="new_lk_autocode")
            else:
                ma_lk_moi = st.text_input("Mã QR LK / VT (Tự viết)", value=auto_code_nm, key="new_lk_manualcode")
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
        # KIỂM TRA TRÙNG TOÀN HỆ THỐNG
        is_duplicate_lk = False
        duplicate_msg_lk = ""
        if not df.empty:
            if ma_lk_moi:
                matched_lk_any = df[df["Ma_LK"] == ma_lk_moi]
                if not matched_lk_any.empty:
                    is_duplicate_lk = True
                    existing_kho = ", ".join(matched_lk_any["Kho_quan_ly"].unique())
                    duplicate_msg_lk = f"⚠️ **CẢNH BÁO TRÙNG MÃ QR:** Mã linh kiện `{ma_lk_moi}` đã tồn tại trong hệ thống (tại **{existing_kho}**)."
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
                tp = r.get("Thanh_phan", [])
                if not m.startswith(("CB", "CM")):
                    if m not in all_items_dict:
                        all_items_dict[m] = {
                            "Ma_LK": m, "Ten_LK": t, "Kho_quan_ly": kho, 
                            "So_luong": sl, "Don_vi": dv, "Hinh_anh": img, 
                            "Quy_cach": qc, "Gia_nhap": gn, "Gia_xuat": gx, "Thanh_phan": []
                        }
                if tp and isinstance(tp, list):
                    for sub_item in tp:
                        sub_m = sub_item.get("ma")
                        sub_t = sub_item.get("ten", "Linh kiện")
                        sub_dv = sub_item.get("dv", "Cái")
                        sub_gia = float(sub_item.get("gia", 0)) if pd.notna(sub_item.get("gia")) else 0
                        sub_img = sub_item.get("img", "")
                        if sub_m and sub_m not in all_items_dict:
                            sub_match_db = df[df["Ma_LK"] == sub_m]
                            if not sub_match_db.empty:
                                db_row = sub_match_db.iloc[0]
                                db_kho = db_row["Kho_quan_ly"] if "Kho_quan_ly" in db_row and pd.notna(db_row["Kho_quan_ly"]) else kho
                                all_items_dict[sub_m] = {
                                    "Ma_LK": sub_m,
                                    "Ten_LK": db_row["Ten_LK"],
                                    "Kho_quan_ly": db_kho,
                                    "So_luong": db_row["So_luong"],
                                    "Don_vi": db_row["Don_vi"],
                                    "Hinh_anh": db_row.get("Hinh_anh", sub_img),
                                    "Quy_cach": int(db_row.get("Quy_cach", 1)),
                                    "Gia_nhap": float(db_row.get("Gia_nhap", sub_gia)),
                                    "Gia_xuat": float(db_row.get("Gia_xuat", 0)),
                                    "Thanh_phan": db_row.get("Thanh_phan", [])
                                }
                            else:
                                all_items_dict[sub_m] = {
                                    "Ma_LK": sub_m,
                                    "Ten_LK": sub_t,
                                    "Kho_quan_ly": kho,
                                    "So_luong": 0,
                                    "Don_vi": sub_dv,
                                    "Hinh_anh": sub_img,
                                    "Quy_cach": 1,
                                    "Gia_nhap": sub_gia,
                                    "Gia_xuat": 0,
                                    "Thanh_phan": []
                                }
        item_dict_le_cu = {}
        for m, info in all_items_dict.items():
            if not m.startswith(("CB", "CM")):
                display_str = f"{m} - {info['Ten_LK']} (Kho: {info['Kho_quan_ly']} | Tồn: {info['So_luong']})"
                item_dict_le_cu[display_str] = info
        col_qr_lc, col_sel_lc = st.columns([2, 2])
        with col_qr_lc:
            scan_qr_lc = st.text_input("📷 Quét mã QR linh kiện cần nhập thêm", placeholder="Quét mã QR sản phẩm...")
            if scan_qr_lc.strip():
                match_qr_lk = scan_qr_lc.strip()
                for d_str, r_info in item_dict_le_cu.items():
                    if r_info["Ma_LK"] == match_qr_lk:
                        st.session_state.selected_lk_nhap_cu = match_qr_lk
                        st.success(f"✨ Đã quét nhận diện linh kiện: `{match_qr_lk}`")
                        break
        if item_dict_le_cu:
            with col_sel_nc:
                lk_keys = list(item_dict_le_cu.keys())
                def_lk_nc_idx = 0
                if st.session_state.selected_lk_nhap_cu:
                    for idx, k in enumerate(lk_keys):
                        if k.startswith(st.session_state.selected_lk_nhap_cu):
                            def_lk_nc_idx = idx
                            break
                chosen_lk_cu_str = st.selectbox("📂 Hoặc chọn từ danh sách:", lk_keys, index=def_lk_nc_idx, key="select_lk_cu_dropdown")
                st.session_state.selected_lk_nhap_cu = chosen_lk_cu_str.split(" - ")[0]
            selected_info = item_dict_le_cu.get(chosen_lk_cu_str, {})
            def_lc_ten = selected_info.get("Ten_LK", "")
            def_lc_kho = selected_info.get("Kho_quan_ly", "Kho 1")
            def_lc_dv = selected_info.get("Don_vi", "Cái")
            def_lc_qc = int(selected_info.get("Quy_cach", 1))
            def_lc_gn = float(selected_info.get("Gia_nhap", 0))
            def_lc_gx = float(selected_info.get("Gia_xuat", 0))
            def_lc_img = selected_info.get("Hinh_anh", "")
            def_lc_tp = selected_info.get("Thanh_phan", [])
            st.info(f"Đang nhập bổ sung cho linh kiện: **{st.session_state.selected_lk_nhap_cu}** ({def_lc_ten})")
            with st.form("nhap_linh_kien_cu_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Tên linh kiện (Cố định)", value=def_lc_ten, disabled=True)
                    st.text_input("Mã QR linh kiện (Cố định)", value=st.session_state.selected_lk_nhap_cu, disabled=True)
                    kho_idx_lc = danh_sach_kho_mac_dinh.index(def_lc_kho) if def_lc_kho in danh_sach_kho_mac_dinh else 0
                    kho_nhap_lc = st.selectbox("🏢 Kho nhập", danh_sach_kho_mac_dinh, index=kho_idx_lc)
                    hinh_thuc_nhap_lc = st.radio("Hình thức nhập kho:", ["📐 Nhập theo đơn vị lẻ", "📦 Nhập theo Kiện (Thùng)"], horizontal=True)
                    so_luong_nhap_them_lc = st.number_input("Số lượng nhập thêm", min_value=0, step=1, value=0)
                    if "📦" in hinh_thuc_nhap_lc:
                        so_luong_thuc_te_lc = so_luong_nhap_them_lc * def_lc_qc
                        st.info(f"💡 Quy đổi: {so_luong_nhap_them_lc} Kiện x {def_lc_qc} = **{so_luong_thuc_te_lc} {def_lc_dv}**")
                    else:
                        so_luong_thuc_te_lc = so_luong_nhap_them_lc
                        st.info(f"💡 Nhập trực tiếp: **{so_luong_thuc_te_lc} {def_lc_dv}**")
                with c2:
                    st.write(f"**Giá nhập hiện tại:** {format_money(def_lc_gn)} VNĐ")
                    st.write(f"**Giá xuất hiện tại:** {format_money(def_lc_gx)} VNĐ")
                    uploaded_phieu_lc = st.file_uploader("📁 Tải ảnh phiếu nhập kho", type=["jpg", "jpeg", "png"], key="up_phieu_lc")
                    img_phieu_lc = st.text_input("Hoặc dán Link ảnh phiếu nhập kho (URL)", key="link_phieu_lc")
                    if uploaded_phieu_lc is not None:
                        img_phieu_lc = f"local_file_{uploaded_phieu_lc.name}"
                        st.image(uploaded_phieu_lc, width=120)
                ghi_chu_lc = st.text_input("Ghi chú nhập thêm", placeholder="Ví dụ: Nhập bổ sung lô hàng cũ")
                submit_lc = st.form_submit_button("💾 Cộng dồn vào kho linh kiện cũ", type="primary", use_container_width=True)
                if submit_lc:
                    if st.session_state.selected_lk_nhap_cu:
                        try:
                            ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            matched_db_lc = df[(df["Ma_LK"] == st.session_state.selected_lk_nhap_cu) & (df["Kho_quan_ly"] == kho_nhap_lc)] if "Kho_quan_ly" in df.columns else pd.DataFrame()
                            current_ton_lc = so_luong_thuc_te_lc
                            old_logs_lc = ""
                            if not matched_db_lc.empty:
                                old_row_lc = matched_db_lc.iloc[0]
                                current_ton_lc = int(old_row_lc["So_luong"]) + int(so_luong_thuc_te_lc)
                                old_logs_lc = old_row_lc.get("Nhat_ky", "")
                            nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung lẻ tại '{kho_nhap_lc}': +{so_luong_thuc_te_lc} {def_lc_dv}"
                            if img_phieu_lc:
                                nhat_ky_str += f" | 📄 [Xem ảnh phiếu nhập]({img_phieu_lc})"
                            if ghi_chu_lc:
                                nhat_ky_str += f" | Ghi chú: {ghi_chu_lc}"
                            if old_logs_lc:
                                nhat_ky_str = old_logs_lc + "\n" + nhat_ky_str
                            update_data_lc = {
                                "Ma_LK": st.session_state.selected_lk_nhap_cu,
                                "Ten_LK": def_lc_ten,
                                "Kho_quan_ly": kho_nhap_lc,
                                "So_luong": int(current_ton_lc),
                                "Don_vi": def_lc_dv,
                                "Nhat_ky": nhat_ky_str,
                                "Hinh_anh": def_lc_img,
                                "Thanh_phan": def_lc_tp,
                                "Gia_nhap": float(def_lc_gn),
                                "Gia_xuat": float(def_lc_gx),
                                "Quy_cach": int(def_lc_qc)
                            }
                            supabase.table("Ton_kho").upsert(update_data_lc).execute()
                            st.success("Đã cộng dồn số lượng vào kho linh kiện cũ thành công!")
                            if img_phieu_lc and img_phieu_lc.startswith("http"):
                                st.image(img_phieu_lc, caption="Ảnh phiếu nhập kho", width=300)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi lưu dữ liệu: {e}")
                    else:
                        st.warning("Vui lòng chọn hoặc quét mã QR linh kiện trước khi lưu!")
        else:
            st.warning("Chưa có linh kiện lẻ nào trong hệ thống!")
    # 8. XÉ LẺ COMBO THÀNH LINH KIỆN
    elif menu_choice == "🔄 Xé lẻ Combo thành Linh kiện":
        st.title("🔄 XÉ LẺ COMBO THÀNH LINH KIỆN (Kit Breaking)")
        st.markdown("---")
        st.info("💡 Chức năng này giúp bạn tháo dỡ bộ Combo nguyên vẹn: **Giảm số lượng Combo** và **Tự động cộng thêm số lượng linh kiện con** vào kho lẻ để sẵn sàng xuất bán/sửa chữa.")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not combo_df.empty:
                break_options = [f"{row['Ma_LK']} - {row['Ten_LK']} (Kho: {row.get('Kho_quan_ly', 'Kho 1')} | Tồn: {row['So_luong']} {row['Don_vi']})" for _, row in combo_df.iterrows()]
                selected_break_opt = st.selectbox("1️⃣ Chọn bộ Combo cần xé lẻ", break_options)
                selected_cb_ma = selected_break_opt.split(" - ")[0]
                cb_row = df[df["Ma_LK"] == selected_cb_ma].iloc[0]
                cb_ten = cb_row["Ten_LK"]
                cb_kho = cb_row.get("Kho_quan_ly", "Kho 1")
                cb_ton = int(cb_row["So_luong"])
                cb_dv = cb_row["Don_vi"]
                cb_tp = cb_row.get("Thanh_phan", [])
                st.warning(f"📦 **Combo chọn:** {cb_ten} (`{selected_cb_ma}`) | Kho: **{cb_kho}** | Tồn kho: **{cb_ton} {cb_dv}**")
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
                                            "Kho_quan_ly": cb_kho,
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
                                            "Kho_quan_ly": cb_kho,
                                            "So_luong": sub_sl_tang,
                                            "Don_vi": sub_dv_con,
                                            "Nhat_ky": sub_log_moi,
                                            "Hinh_anh": tp.get("img", ""),
                                            "Thanh_phan": []
                                        }).execute()
                                st.success("Xé lẻ Combo thành công! Đã trừ số lượng bộ Combo và tự động cộng bù linh kiện con vào kho.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi thực hiện xé lẻ: {e}")
                else:
                    st.info("Bộ Combo này chưa khai báo định mức linh kiện thành phần ở Phần 2.")
            else:
                st.warning("Hiện chưa có mã Combo nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 9. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO (Tự động trừ định mức linh kiện/vật tư con)")
        st.markdown("---")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not combo_df.empty:
                col_ex_sc1, col_ex_sc2 = st.columns([2, 2])
                with col_ex_sc1:
                    qr_export_cb = st.text_input("📷 Quét mã QR Combo cần xuất", placeholder="Quét mã QR sản phẩm...")
                target_cb_ma = None
                if qr_export_cb.strip():
                    m_cb = qr_export_cb.strip()
                    matched_cb_qr = combo_df[combo_df["Ma_LK"] == m_cb]
                    if not matched_cb_qr.empty:
                        target_cb_ma = matched_cb_qr.iloc[0]["Ma_LK"]
                        st.success(f"✨ Đã nhận diện Combo: **{matched_cb_qr.iloc[0]['Ten_LK']}** (`{target_cb_ma}`)")
                    else:
                        st.warning("⚠️ Không tìm thấy Combo nào khớp với mã QR này.")
                export_options = [f"{row['Ma_LK']} - {row['Ten_LK']} (Kho: {row.get('Kho_quan_ly', 'Kho 1')})" for _, row in combo_df.iterrows()]
                default_cb_idx = 0
                if target_cb_ma:
                    for idx, opt in enumerate(export_options):
                        if opt.startswith(target_cb_ma):
                            default_cb_idx = idx
                            break
                with col_ex_sc2:
                    selected_export_opt = st.selectbox("1️⃣ Hoặc chọn Combo từ danh sách", export_options, index=default_cb_idx)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
                hien_thi_ten = current_item_row["Ten_LK"]
                kho_xuat_cb = current_item_row.get("Kho_quan_ly", "Kho 1")
                ton_hien_tai = current_item_row["So_luong"]
                don_vi_tinh = current_item_row["Don_vi"]
                hinh_anh_cu = current_item_row["Hinh_anh"]
                thanh_phan_list = current_item_row.get("Thanh_phan", [])
                quy_cach_cb = int(current_item_row.get("Quy_cach", 1))
                st.warning(f"📦 **Combo chọn:** {hien_thi_ten} (`{selected_export_item}`) | Kho: **{kho_xuat_cb}** | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}** (1 Kiện = {quy_cach_cb} {don_vi_tinh})")
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
                    uploaded_phieu_xuat_cb = st.file_uploader("📁 Tải ảnh phiếu xuất kho (hoặc chụp phiếu)", type=["jpg", "jpeg", "png"], key="up_phieu_xuat_cb")
                    img_phieu_xuat_cb = st.text_input("Hoặc dán Link ảnh phiếu xuất kho (URL)", key="ex_phieu_cb")
                    if uploaded_phieu_xuat_cb is not None:
                        img_phieu_xuat_cb = f"local_file_{uploaded_phieu_xuat_cb.name}"
                        st.image(uploaded_phieu_xuat_cb, width=120)
                    export_btn = st.form_submit_button("Xác nhận Xuất Combo")
                    if export_btn:
                        try:
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                            so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                            nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất Combo tại kho '{kho_xuat_cb}': {so_luong_xuat} {don_vi_tinh}"
                            if img_phieu_xuat_cb:
                                nhat_ky_xuat += f" | 📄 [Xem ảnh phiếu xuất]({img_phieu_xuat_cb})"
                            if noi_dung_xuat:
                                nhat_ky_xuat += f" | Nội dung: {noi_dung_xuat}"
                            update_data = {
                                "Ma_LK": selected_export_item,
                                "Ten_LK": hien_thi_ten,
                                "Kho_quan_ly": kho_xuat_cb,
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
                            if img_phieu_xuat_cb and img_phieu_xuat_cb.startswith("http"):
                                st.image(img_phieu_xuat_cb, caption="Ảnh phiếu xuất kho", width=300)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thực hiện xuất kho: {e}")
            else:
                st.warning("Hiện chưa có mã Combo nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 10. XUẤT KHO LINH KIỆN LẺ
    elif menu_choice == "📤 Xuất kho Linh kiện lẻ":
        st.title("📤 XUẤT KHO LINH KIỆN / VẬT TƯ LẺ (Độc lập & Thành phần)")
        st.markdown("---")
        if not df.empty:
            all_items_dict = {}
            for _, row in df.iterrows():
                m = row["Ma_LK"]
                t = row["Ten_LK"]
                kho = row.get("Kho_quan_ly", "Kho 1")
                dv = row["Don_vi"]
                sl = row["So_luong"]
                img = row.get("Hinh_anh", "")
                qc = int(row.get("Quy_cach", 1))
                if not m.startswith(("CB", "CM")):
                    if m not in all_items_dict:
                        all_items_dict[m] = {"Ten_LK": t, "Kho_quan_ly": kho, "So_luong": sl, "Don_vi": dv, "Hinh_anh": img, "Quy_cach": qc}
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
                                    "Kho_quan_ly": sub_match.iloc[0].get("Kho_quan_ly", "Kho 1"),
                                    "So_luong": sub_match.iloc[0]["So_luong"],
                                    "Don_vi": sub_match.iloc[0]["Don_vi"],
                                    "Hinh_anh": sub_match.iloc[0].get("Hinh_anh", ""),
                                    "Quy_cach": int(sub_match.iloc[0].get("Quy_cach", 1))
                                }
                            else:
                                all_items_dict[sub_m] = {
                                    "Ten_LK": sub_name,
                                    "Kho_quan_ly": kho,
                                    "So_luong": 0,
                                    "Don_vi": sub_dv,
                                    "Hinh_anh": tp.get("img", ""),
                                    "Quy_cach": 1
                                }
            col_ex_sc3, col_ex_sc4 = st.columns([2, 2])
            with col_ex_sc3:
                qr_export_le = st.text_input("📷 Quét mã QR linh kiện cần xuất", placeholder="Quét mã QR sản phẩm...")
            target_le_ma = None
            if qr_export_le.strip():
                m_lk = qr_export_le.strip()
                if m_lk in all_items_dict:
                    target_le_ma = m_lk
                    st.success(f"✨ Đã nhận diện: **{all_items_dict[m_lk]['Ten_LK']}** (`{target_le_ma}`)")
                else:
                    st.warning("⚠️ Không tìm thấy linh kiện nào khớp với mã QR này.")
            export_options = [f"{m} - {info['Ten_LK']} (Kho: {info['Kho_quan_ly']})" for m, info in all_items_dict.items()]
            default_le_idx = 0
            if target_le_ma:
                for idx, opt in enumerate(export_options):
                    if opt.startswith(target_le_ma):
                        default_le_idx = idx
                        break
            if export_options:
                with col_ex_sc4:
                    selected_export_opt = st.selectbox("1️⃣ Hoặc chọn linh kiện từ danh sách", export_options, index=default_le_idx)
                selected_export_item = selected_export_opt.split(" - ")[0]
                current_info = all_items_dict[selected_export_item]
                hien_thi_ten = current_info["Ten_LK"]
                kho_xuat_le = current_info["Kho_quan_ly"]
                ton_hien_tai = current_info["So_luong"]
                don_vi_tinh = current_info["Don_vi"]
                hinh_anh_cu = current_info["Hinh_anh"]
                quy_cach_le_xuat = current_info["Quy_cach"]
                st.warning(f"🔩 **Linh kiện/Vật tư chọn:** {hien_thi_ten} (`{selected_export_item}`) | Kho: **{kho_xuat_le}** | Tồn kho hiện tại: **{ton_hien_tai} {don_vi_tinh}** (1 Kiện = {quy_cach_le_xuat} {don_vi_tinh})")
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
                    uploaded_phieu_xuat_le = st.file_uploader("📁 Tải ảnh phiếu xuất kho (hoặc chụp phiếu)", type=["jpg", "jpeg", "png"], key="up_phieu_xuat_le")
                    img_phieu_xuat_le = st.text_input("Hoặc dán Link ảnh phiếu xuất kho (URL)", key="ex_phieu_le")
                    if uploaded_phieu_xuat_le is not None:
                        img_phieu_xuat_le = f"local_file_{uploaded_phieu_xuat_le.name}"
                        st.image(uploaded_phieu_xuat_le, width=120)
                    export_btn = st.form_submit_button("Xác nhận Xuất Linh kiện/Vật tư")
                    if export_btn:
                        try:
                            nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                            ngay_gio_str = ngay_xuat.strftime("%d/%m/%Y") + " " + datetime.now().strftime("%H:%M")
                            so_luong_moi = int(ton_hien_tai) - int(so_luong_xuat)
                            nhat_ky_xuat = f"[{ngay_gio_str}] 👤 {nguoi_thuc_hien} - 📤 Xuất lẻ tại kho '{kho_xuat_le}': {so_luong_xuat} {don_vi_tinh}"
                            if img_phieu_xuat_le:
                                nhat_ky_xuat += f" | 📄 [Xem ảnh phiếu xuất]({img_phieu_xuat_le})"
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
                                "Kho_quan_ly": kho_xuat_le,
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
                            if img_phieu_xuat_le and img_phieu_xuat_le.startswith("http"):
                                st.image(img_phieu_xuat_le, caption="Ảnh phiếu xuất kho", width=300)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thực hiện xuất kho: {e}")
            else:
                st.warning("Hiện chưa có mã linh kiện/vật tư nào trong hệ thống!")
        else:
            st.warning("Kho hiện đang trống!")
    # 11. BÁO CÁO & XUẤT EXCEL
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        st.markdown("---")
        st.info("💡 Bạn có thể tải toàn bộ dữ liệu tồn kho dưới dạng file **Excel (.xlsx)**.")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach"]].copy()
                df_ton_kho.columns = ["Mã QR Sản Phẩm / Combo", "Tên Sản Phẩm", "Kho Quản Lý", "Số Lượng Tồn Kho", "Đơn Vị Tính", "Quy Cách (SL/Kiện)"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho_Hien_Tai', index=False)
                df_nhat_ky = df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "Nhat_ky"]].copy()
                df_nhat_ky.columns = ["Mã QR Sản Phẩm", "Tên Sản Phẩm", "Kho Quản Lý", "Lịch Sử Nhật Ký Chi Tiết"]
                df_nhat_ky.to_excel(writer, sheet_name='Lich_Su_Nhat_Ky', index=False)
            excel_data = output.getvalue()
            time_stamp = datetime.now().strftime("%Y%m%d_%H%M")
            col_rep1, col_rep2 = st.columns(2)
            with col_rep1:
                st.metric("Tổng số mặt hàng / Combo", len(df["Ma_LK"].unique()))
                st.metric("Tổng lượng kho", int(df["So_luong"].sum()) if "So_luong" in df else 0)
            with col_rep2:
                st.download_button(
                    label="📥 Tải Báo Cáo Kho Dạng Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"Bao_Cao_Da_Kho_{time_stamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("Kho hiện đang trống!")
