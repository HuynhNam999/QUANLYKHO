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
                st.subheader("🔍 Chọn sản phẩm & Quét mã")
                # Quét ảnh QR an toàn (hỗ trợ kiểm tra thư viện cv2)
                img_qr_scan = st.file_uploader("📷 CHỤP ẢNH / TẢI ẢNH MÃ QR ĐỂ QUÉT NHANH", type=["jpg", "jpeg", "png"], key="pos_qr_img_upload")
                scanned_from_image = None
                if img_qr_scan is not None:
                    try:
                        image_pil = Image.open(img_qr_scan)
                        import numpy as np
                        try:
                            import cv2
                            opencv_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
                            detector = cv2.QRCodeDetector()
                            data_qr, bbox, _ = detector.detectAndDecode(opencv_image)
                            if data_qr:
                                scanned_from_image = data_qr.strip()
                            else:
                                # Thử dùng pyzbar nếu có sẵn
                                try:
                                    from pyzbar.pyzbar import decode
                                    decoded_objects = decode(image_pil)
                                    if decoded_objects:
                                        scanned_from_image = decoded_objects[0].data.decode('utf-8').strip()
                                except ImportError:
                                    pass
                        except ImportError:
                            # Nếu thiếu cv2, hiển thị hướng dẫn đơn giản hoặc dùng thư viện thay thế
                            st.warning("⚠️ Máy chủ đang thiếu module `cv2`. Vui lòng thêm `opencv-python-headless` vào file `requirements.txt` trên GitHub của bạn.")
                        if scanned_from_image:
                            st.success(f"✨ Quét thành công mã từ ảnh: `{scanned_from_image}`")
                        else:
                            st.warning("⚠️ Không tìm thấy mã QR trong ảnh. Hãy thử chụp rõ nét hơn hoặc nhập mã trực tiếp bên dưới.")
                    except Exception as e:
                        st.error(f"Không thể đọc ảnh QR: {e}")
                scanned_code_input = st.text_input("⌨️ Hoặc dùng máy quét USB / Nhập mã thủ công:", value=scanned_from_image if scanned_from_image else "", placeholder="Bắn máy quét hoặc gõ mã...")
                selected_code_pos = None
                active_scan_code = scanned_code_input.strip()
                if active_scan_code:
                    if active_scan_code in all_sellable_items:
                        selected_code_pos = active_scan_code
                        st.success(f"✨ Đã nhận diện sản phẩm: **{all_sellable_items[active_scan_code]['Ten_LK']}**")
                    else:
                        st.warning(f"⚠️ Mã `{active_scan_code}` không tồn tại trong kho bán hàng.")
                options_pos = [f"{m} - {info['Ten_LK']} (Tồn: {info['So_luong']} {info['Don_vi']} | Giá: {format_money(info['Gia_xuat'])}đ)" for m, info in all_sellable_items.items()]
                default_pos_idx = 0
                if selected_code_pos:
                    for idx, opt in enumerate(options_pos):
                        if opt.startswith(selected_code_pos):
                            default_pos_idx = idx
                            break
                chosen_opt_pos = st.selectbox("📦 Hoặc chọn nhanh từ danh sách:", options_pos, index=default_pos_idx)
                chosen_m_pos = chosen_opt_pos.split(" - ")[0]
                item_info = all_sellable_items[chosen_m_pos]
                st.write(f"**Giá bán:** `{format_money(item_info['Gia_xuat'])} VNĐ / {item_info['Don_vi']}`")
                st.write(f"**Tồn kho hiện tại:** `{item_info['So_luong']} {item_info['Don_vi']}` (Kho: {item_info['Kho_quan_ly']})")
                sl_mua = st.number_input("Số lượng mua", min_value=1, max_value=max(1, int(item_info['So_luong'])), step=1, value=1)
                if st.button("➕ Thêm vào giỏ hàng", type="primary"):
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
                    if st.button("🗑️ Xóa sạch giỏ hàng"):
                        st.session_state.cart = []
                        st.rerun()
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
                                        supabase.table("Ton_kho").update({
                                            "So_luong": ton_moi,
                                            "Nhat_ky": log_str
                                        }).eq("Ma_LK", m_lk).eq("Kho_quan_ly", kho).execute()
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
    # Các chức năng khác giữ nguyên như cũ...
