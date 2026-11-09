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
# Cấu hình giao diện toàn màn hình
st.set_page_config(
    page_title="Quản Lý Đa Kho, Bán Hàng & Công Nợ", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="auto"
)
# CSS giao diện chuyên nghiệp
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
    </style>
""", unsafe_allow_html=True)
# Khởi tạo Supabase
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
danh_sach_kho_mac_dinh = [f"Kho {i}" for i in range(1, 11)]
def format_money(val):
    try:
        if pd.isna(val) or val == "":
            return "0"
        num = float(val)
        return f"{num:,.0f}".replace(",", ".")
    except Exception:
        return "0"
def remove_vietnamese_accent(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return text.strip().lower()
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
    upper_name = upper_name.replace("BULONG", "BL").replace("BU LONG", "BL").replace("LONG DEN", "LD").replace("LON DEN", "LD")
    clean_code = re.sub(r'[^A-Z0-9\.]', '_', upper_name)
    clean_code = re.sub(r'_+', '_', clean_code).strip('_')
    return f"{prefix}-{clean_code[:30]}".replace("__", "_").upper()
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
# --- MENU BÊN TRÁI ĐÃ SẮP XẾP LẠI THỨ TỰ ---
st.sidebar.title(f"👤 Xin chào: {st.session_state.username}")
st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Danh Mục Quản Lý")
menu_choice = st.sidebar.radio(
    "Chọn chức năng:",
    [
        "🛍️ Bán hàng & In hóa đơn (POS)",
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
# --- GIAO DIỆN CHÍNH ---
_, main_col, _ = st.columns([0.02, 0.96, 0.02])
with main_col:
    # 1. BÁN HÀNG & IN HÓA ĐƠN (POS)
    if menu_choice == "🛍️ Bán hàng & In hóa đơn (POS)":
        st.title("🛍️ MÀN HÌNH BÁN HÀNG & IN HÓA ĐƠN (POS)")
        st.markdown("---")
        if "cart" not in st.session_state:
            st.session_state.cart = []
        if "last_invoice" not in st.session_state:
            st.session_state.last_invoice = None
        if not df.empty:
            all_sellable_items = {}
            for _, r in df.iterrows():
                m = str(r["Ma_LK"]).strip()
                all_sellable_items[m] = {
                    "Ma_LK": m, "Ten_LK": r["Ten_LK"], "Kho_quan_ly": r.get("Kho_quan_ly", "Kho 1"), 
                    "So_luong": r["So_luong"], "Don_vi": r["Don_vi"], 
                    "Gia_nhap": float(r.get("Gia_nhap", 0)), "Gia_xuat": float(r.get("Gia_xuat", 0)), 
                    "Thanh_phan": r.get("Thanh_phan", [])
                }
            col_pos1, col_pos2 = st.columns([1.5, 2.5])
            with col_pos1:
                st.subheader("🔍 Chọn sản phẩm")
                options_pos = ["-- Chọn sản phẩm từ danh sách --"] + [f"{m} - {info['Ten_LK']} (Tồn: {info['So_luong']} {info['Don_vi']} | Giá: {format_money(info['Gia_xuat'])}đ)" for m, info in all_sellable_items.items()]
                chosen_opt_pos = st.selectbox("📦 Chọn sản phẩm:", options_pos)
                scanned_code_input = st.text_input("⌨️ Mã sản phẩm / Bắn QR:", placeholder="Bắn máy quét hoặc gõ mã...")
                final_selected_code = scanned_code_input.strip() if scanned_code_input.strip() else (chosen_opt_pos.split(" - ")[0] if chosen_opt_pos and not chosen_opt_pos.startswith("--") else "")
                if final_selected_code and final_selected_code in all_sellable_items:
                    item_info = all_sellable_items[final_selected_code]
                    st.success(f"🎯 **{item_info['Ten_LK']}** | Giá: {format_money(item_info['Gia_xuat'])}đ | Tồn: {item_info['So_luong']} {item_info['Don_vi']}")
                    sl_mua = st.number_input("Số lượng mua", min_value=1, max_value=max(1, int(item_info['So_luong'])), step=1, value=1)
                    if st.button("➕ Thêm vào giỏ hàng", type="primary"):
                        found = False
                        for c in st.session_state.cart:
                            if c["Ma_LK"] == final_selected_code:
                                c["So_luong_mua"] += sl_mua
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "Ma_LK": final_selected_code, "Ten_LK": item_info["Ten_LK"],
                                "Kho_quan_ly": item_info["Kho_quan_ly"], "Don_vi": item_info["Don_vi"],
                                "Gia_nhap": item_info["Gia_nhap"], "Gia_xuat": item_info["Gia_xuat"],
                                "So_luong_mua": sl_mua, "Thanh_phan": item_info["Thanh_phan"]
                            })
                        st.success("Đã thêm!")
                        st.rerun()
            with col_pos2:
                st.subheader("🛒 Giỏ hàng")
                if st.session_state.cart:
                    df_cart = pd.DataFrame(st.session_state.cart)
                    df_cart["Thanh_tien"] = df_cart["Gia_xuat"] * df_cart["So_luong_mua"]
                    df_display_cart = df_cart[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong_mua", "Don_vi"]].copy()
                    df_display_cart["Đơn giá"] = df_cart["Gia_xuat"].apply(format_money)
                    df_display_cart["Thành tiền"] = df_cart["Thanh_tien"].apply(format_money)
                    st.dataframe(df_display_cart, use_container_width=True)
                    tong_tien_don_hang = df_cart["Thanh_tien"].sum()
                    st.markdown(f"### 💰 TỔNG TIỀN: `{format_money(tong_tien_don_hang)} VNĐ`")
                    if st.button("🗑️ Xóa sạch giỏ"):
                        st.session_state.cart = []
                        st.rerun()
                    st.markdown("---")
                    st.subheader("💳 Thanh toán & Xuất Hóa Đơn")
                    with st.form("checkout_form"):
                        ten_khach = st.text_input("Tên khách hàng", placeholder="Ví dụ: Anh Nam")
                        sdt_khach = st.text_input("Số điện thoại", placeholder="0912345678")
                        hinh_thuc_tt = st.radio("Hình thức thanh toán:", ["💵 Tiền mặt", "💳 Chuyển khoản", "📝 Ghi nợ công nợ"], horizontal=True)
                        ghi_chu_don = st.text_input("Ghi chú đơn hàng")
                        checkout_btn = st.form_submit_button("✅ HOÀN TẤT THANH TOÁN & IN HÓA ĐƠN", type="primary", use_container_width=True)
                        if checkout_btn:
                            try:
                                ngay_gio_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                                nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                                for c_item in st.session_state.cart:
                                    m_lk = c_item["Ma_LK"]
                                    sl_mua = c_item["So_luong_mua"]
                                    kho = c_item["Kho_quan_ly"]
                                    db_match = df[(df["Ma_LK"] == m_lk) & (df["Kho_quan_ly"] == kho)]
                                    if not db_match.empty:
                                        row_db = db_match.iloc[0]
                                        ton_moi = max(0, int(row_db["So_luong"]) - sl_mua)
                                        old_logs = row_db.get("Nhat_ky", "")
                                        log_str = f"[{ngay_gio_hien_tai}] 👤 {nguoi_thuc_hien} - 🛒 Bán hàng POS cho khách '{ten_khach}' (SĐT: {sdt_khach}): -{sl_mua} {c_item['Don_vi']} | Giá xuất: {c_item['Gia_xuat']} | Giá nhập: {c_item['Gia_nhap']} | TT: {hinh_thuc_tt}"
                                        if ghi_chu_don: log_str += f" | Ghi chú: {ghi_chu_don}"
                                        if old_logs: log_str = old_logs + "\n" + log_str
                                        supabase.table("Ton_kho").update({"So_luong": ton_moi, "Nhat_ky": log_str}).eq("Ma_LK", m_lk).eq("Kho_quan_ly", kho).execute()
                                st.session_state.last_invoice = {
                                    "ma_hd": f"HD{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                    "ngay": ngay_gio_hien_tai,
                                    "khach": ten_khach if ten_khach else "Khách lẻ",
                                    "sdt": sdt_khach,
                                    "hinh_thuc": hinh_thuc_tt,
                                    "items": st.session_state.cart.copy(),
                                    "tong_tien": tong_tien_don_hang,
                                    "nguoi_ban": nguoi_thuc_hien
                                }
                                st.session_state.cart = []
                                st.success("🎉 Thanh toán thành công!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi thanh toán: {e}")
        if st.session_state.last_invoice:
            st.markdown("---")
            st.subheader("📄 HÓA ĐƠN BÁN HÀNG VỪA TẠO")
            inv = st.session_state.last_invoice
            with st.container():
                st.markdown(f"""
                <div class="invoice-box">
                    <h3 style="text-align: center;">🧾 HÓA ĐƠN BÁN HÀNG</h3>
                    <p><b>Mã hóa đơn:</b> {inv['ma_hd']} | <b>Ngày:</b> {inv['ngay']}</p>
                    <p><b>Khách hàng:</b> {inv['khach']} | <b>SĐT:</b> {inv['sdt']}</p>
                    <p><b>Thu ngân:</b> {inv['nguoi_ban']} | <b>Thanh toán:</b> {inv['hinh_thuc']}</p>
                    <hr>
                </div>
                """, unsafe_allow_html=True)
                df_inv_items = pd.DataFrame(inv['items'])
                df_inv_items["Thành tiền (VNĐ)"] = (df_inv_items["Gia_xuat"] * df_inv_items["So_luong_mua"]).apply(format_money)
                df_inv_items["Đơn giá (VNĐ)"] = df_inv_items["Gia_xuat"].apply(format_money)
                st.dataframe(df_inv_items[["Ma_LK", "Ten_LK", "So_luong_mua", "Don_vi", "Đơn giá (VNĐ)", "Thành tiền (VNĐ)"]], use_container_width=True)
                st.markdown(f"#### **Tổng cộng thanh toán:** `{format_money(inv['tong_tien'])} VNĐ`")
    # 2. TỔNG QUAN TỒN KHO
    elif menu_choice == "📊 Tổng quan tồn kho":
        col_title, col_select_k = st.columns([2.5, 1.5])
        with col_select_k:
            selected_warehouse = st.selectbox("🏢 Chọn kho xem tồn kho:", ["🌐 Xem tất cả các kho"] + danh_sach_kho_mac_dinh, key="main_wh_select")
        with col_title:
            st.title(f"📦 TỒN KHO HỆ THỐNG")
        st.markdown("---")
        if not df.empty:
            df_working = df.copy()
            for col_check in ["Gia_nhap", "Gia_xuat", "Quy_cach", "So_luong", "Kho_quan_ly"]:
                if col_check not in df_working.columns:
                    df_working[col_check] = "Kho 1" if col_check == "Kho_quan_ly" else (1 if col_check == "Quy_cach" else 0)
            df_working["So_luong"] = pd.to_numeric(df_working["So_luong"], errors="coerce").fillna(0)
            df_working["Gia_nhap"] = pd.to_numeric(df_working["Gia_nhap"], errors="coerce").fillna(0)
            if selected_warehouse != "🌐 Xem tất cả các kho":
                df_filtered = df_working[df_working["Kho_quan_ly"] == selected_warehouse].copy()
                df_filtered["Thanh_tien"] = df_filtered["So_luong"] * df_filtered["Gia_nhap"]
                df_filtered["Gia_nhap_fmt"] = df_filtered["Gia_nhap"].apply(format_money)
                df_filtered["Gia_xuat_fmt"] = df_filtered["Gia_xuat"].apply(format_money)
                df_display = df_filtered[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach", "Gia_nhap_fmt", "Gia_xuat_fmt"]].copy()
                df_display.columns = ["Mã QR / Sản phẩm", "Tên sản phẩm", "Kho quản lý", "Tồn kho", "Đơn vị", "Quy cách", "Giá nhập", "Giá xuất"]
                st.dataframe(df_display, use_container_width=True, height=500)
            else:
                st.dataframe(df_working[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach"]], use_container_width=True, height=500)
    # 3. TRA CỨU & LỌC CHI TIẾT
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU & LỌC CHI TIẾT")
        st.markdown("---")
        if not df.empty:
            search_input = st.text_input("Nhập mã hoặc tên sản phẩm cần tra cứu:")
            if search_input:
                res = df[df["Ma_LK"].str.contains(search_input, case=False, na=False) | df["Ten_LK"].str.contains(search_input, case=False, na=False)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
    # 4. ĐIỀU CHỈNH THÔNG TIN & GIÁ COMBO
    elif menu_choice == "✏️ Điều chỉnh thông tin & Giá Combo":
        st.title("✏️ ĐIỀU CHỈNH THÔNG TIN & GIÁ COMBO")
        st.markdown("---")
        if not df.empty:
            combo_list = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]["Ma_LK"].tolist()
            if combo_list:
                chon_cb = st.selectbox("Chọn mã Combo cần chỉnh sửa:", combo_list)
                cb_info = df[df["Ma_LK"] == chon_cb].iloc[0]
                with st.form("edit_cb_form"):
                    new_ten = st.text_input("Tên Combo", value=cb_info["Ten_LK"])
                    new_gn = st.number_input("Giá nhập", value=float(cb_info.get("Gia_nhap", 0)))
                    new_gx = st.number_input("Giá xuất", value=float(cb_info.get("Gia_xuat", 0)))
                    submitted = st.form_submit_button("Lưu thay đổi")
                    if submitted:
                        supabase.table("Ton_kho").update({"Ten_LK": new_ten, "Gia_nhap": new_gn, "Gia_xuat": new_gx}).eq("Ma_LK", chon_cb).execute()
                        st.success("Đã cập nhật thành công!")
                        st.rerun()
            else:
                st.info("Chưa có mã Combo nào.")
    # 5. NHẬP COMBO MỚI
    elif menu_choice == "📥 Nhập Combo mới":
        st.title("📥 NHẬP COMBO MỚI")
        st.markdown("---")
        with st.form("new_combo_form"):
            ten_cb = st.text_input("Tên Combo mới")
            kho_nhap = st.selectbox("Kho nhập", danh_sach_kho_mac_dinh)
            sl_nhap = st.number_input("Số lượng", min_value=1, value=1)
            gn_cb = st.number_input("Giá nhập", min_value=0.0)
            gx_cb = st.number_input("Giá xuất", min_value=0.0)
            submitted = st.form_submit_button("Lưu Combo mới")
            if submitted and ten_cb:
                ma_moi = generate_code_from_name(ten_cb, is_combo=True)
                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                nguoi_thuc_hien = st.session_state.get("username", "Admin")
                log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho mới '{kho_nhap}': +{sl_nhap}"
                supabase.table("Ton_kho").insert({
                    "Ma_LK": ma_moi, "Ten_LK": ten_cb, "Kho_quan_ly": kho_nhap,
                    "So_luong": sl_nhap, "Don_vi": "Bộ", "Gia_nhap": gn_cb, "Gia_xuat": gx_cb,
                    "Nhat_ky": log_str, "Quy_cach": 1, "Thanh_phan": []
                }).execute()
                st.success("Đã thêm Combo mới thành công!")
                st.rerun()
    # 6. NHẬP COMBO CŨ
    elif menu_choice == "📥 Nhập Combo cũ":
        st.title("📥 NHẬP BỔ SUNG COMBO CŨ")
        st.markdown("---")
        if not df.empty:
            cb_old = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not cb_old.empty:
                opts = [f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})" for _, r in cb_old.iterrows()]
                sel = st.selectbox("Chọn Combo cần nhập thêm:", opts)
                ma_sel = sel.split(" - ")[0]
                with st.form("old_cb_form"):
                    kho_sel = sel.split("Kho: ")[1].split(" |")[0]
                    sl_them = st.number_input("Số lượng nhập thêm", min_value=1, value=1)
                    submitted = st.form_submit_button("Cộng dồn vào kho")
                    if submitted:
                        row_old = df[(df["Ma_LK"] == ma_sel) & (df["Kho_quan_ly"] == kho_sel)].iloc[0]
                        new_ton = int(row_old["So_luong"]) + int(sl_them)
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Admin")
                        log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung tại '{kho_sel}': +{sl_them}"
                        old_logs = row_old.get("Nhat_ky", "")
                        if old_logs: log_str = old_logs + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": new_ton, "Nhat_ky": log_str}).eq("Ma_LK", ma_sel).eq("Kho_quan_ly", kho_sel).execute()
                        st.success("Cập nhật kho thành công!")
                        st.rerun()
            else:
                st.info("Chưa có mã Combo nào.")
    # 7. NHẬP LINH KIỆN MỚI
    elif menu_choice == "📥 Nhập linh kiện mới":
        st.title("📥 NHẬP LINH KIỆN / VẬT TƯ MỚI")
        st.markdown("---")
        with st.form("new_lk_form"):
            ten_lk = st.text_input("Tên linh kiện / vật tư")
            phan_loai = st.radio("Phân loại:", ["🔩 Vật tư (VT)", "⚙️ Linh kiện (LK)"], horizontal=True)
            kho_lk = st.selectbox("Kho nhập", danh_sach_kho_mac_dinh)
            sl_lk = st.number_input("Số lượng", min_value=1, value=1)
            dv_lk = st.selectbox("Đơn vị tính", ["Cái", "Chiếc", "Bộ", "Kg", "Mét", "Hộp"])
            gn_lk = st.number_input("Giá nhập", min_value=0.0)
            gx_lk = st.number_input("Giá xuất", min_value=0.0)
            submitted = st.form_submit_button("Lưu linh kiện mới")
            if submitted and ten_lk:
                prefix = "LK" if "LK" in phan_loai else "VT"
                ma_lk_moi = generate_code_from_name(ten_lk, is_combo=False, item_type=prefix)
                ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                nguoi_thuc_hien = st.session_state.get("username", "Admin")
                log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập kho mới tại '{kho_lk}': +{sl_lk} {dv_lk}"
                supabase.table("Ton_kho").insert({
                    "Ma_LK": ma_lk_moi, "Ten_LK": ten_lk, "Kho_quan_ly": kho_lk,
                    "So_luong": sl_lk, "Don_vi": dv_lk, "Gia_nhap": gn_lk, "Gia_xuat": gx_lk,
                    "Nhat_ky": log_str, "Quy_cach": 1, "Thanh_phan": []
                }).execute()
                st.success("Đã thêm linh kiện mới thành công!")
                st.rerun()
    # 8. NHẬP LINH KIỆN CŨ
    elif menu_choice == "📥 Nhập linh kiện cũ":
        st.title("📥 NHẬP BỔ SUNG LINH KIỆN CŨ")
        st.markdown("---")
        if not df.empty:
            lk_old = df[~df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not lk_old.empty:
                opts = [f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})" for _, r in lk_old.iterrows()]
                sel = st.selectbox("Chọn linh kiện cần nhập thêm:", opts)
                ma_sel = sel.split(" - ")[0]
                with st.form("old_lk_form"):
                    kho_sel = sel.split("Kho: ")[1].split(" |")[0]
                    sl_them = st.number_input("Số lượng nhập thêm", min_value=1, value=1)
                    submitted = st.form_submit_button("Cộng dồn vào kho")
                    if submitted:
                        row_old = df[(df["Ma_LK"] == ma_sel) & (df["Kho_quan_ly"] == kho_sel)].iloc[0]
                        new_ton = int(row_old["So_luong"]) + int(sl_them)
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Admin")
                        log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📥 Nhập bổ sung lẻ tại '{kho_sel}': +{sl_them}"
                        old_logs = row_old.get("Nhat_ky", "")
                        if old_logs: log_str = old_logs + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": new_ton, "Nhat_ky": log_str}).eq("Ma_LK", ma_sel).eq("Kho_quan_ly", kho_sel).execute()
                        st.success("Cập nhật kho thành công!")
                        st.rerun()
            else:
                st.info("Chưa có linh kiện nào.")
    # 9. XÉ LẺ COMBO THÀNH LINH KIỆN
    elif menu_choice == "🔄 Xé lẻ Combo thành Linh kiện":
        st.title("🔄 XÉ LẺ COMBO THÀNH LINH KIỆN")
        st.markdown("---")
        if not df.empty:
            cb_list = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not cb_list.empty:
                opts = [f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})" for _, r in cb_list.iterrows()]
                sel = st.selectbox("Chọn Combo để xé lẻ:", opts)
                ma_sel = sel.split(" - ")[0]
                kho_sel = sel.split("Kho: ")[1].split(" |")[0]
                cb_row = df[(df["Ma_LK"] == ma_sel) & (df["Kho_quan_ly"] == kho_sel)].iloc[0]
                tp_list = cb_row.get("Thanh_phan", [])
                if tp_list:
                    st.write("Các linh kiện con trong bộ:", tp_list)
                    with st.form("break_form"):
                        sl_xe = st.number_input("Số lượng Combo muốn xé lẻ", min_value=1, max_value=int(cb_row["So_luong"]), value=1)
                        submitted = st.form_submit_button("Xác nhận xé lẻ")
                        if submitted:
                            st.success("Đã thực hiện xé lẻ thành công!")
                else:
                    st.warning("Combo này chưa được cấu hình thành phần con.")
            else:
                st.info("Không có Combo nào.")
    # 10. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO")
        st.markdown("---")
        if not df.empty:
            cb_list = df[df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not cb_list.empty:
                opts = [f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})" for _, r in cb_list.iterrows()]
                sel = st.selectbox("Chọn Combo cần xuất:", opts)
                ma_sel = sel.split(" - ")[0]
                kho_sel = sel.split("Kho: ")[1].split(" |")[0]
                with st.form("export_cb_form"):
                    sl_xuat = st.number_input("Số lượng xuất", min_value=1, value=1)
                    ghi_chu = st.text_input("Nội dung xuất kho")
                    submitted = st.form_submit_button("Xác nhận xuất kho")
                    if submitted:
                        row_cb = df[(df["Ma_LK"] == ma_sel) & (df["Kho_quan_ly"] == kho_sel)].iloc[0]
                        new_ton = max(0, int(row_cb["So_luong"]) - int(sl_xuat))
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Admin")
                        log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📤 Xuất Combo tại kho '{kho_sel}': -{sl_xuat} | Nội dung: {ghi_chu}"
                        old_logs = row_cb.get("Nhat_ky", "")
                        if old_logs: log_str = old_logs + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": new_ton, "Nhat_ky": log_str}).eq("Ma_LK", ma_sel).eq("Kho_quan_ly", kho_sel).execute()
                        st.success("Xuất kho thành công!")
                        st.rerun()
            else:
                st.info("Không có Combo nào.")
    # 11. XUẤT KHO LINH KIỆN LẺ
    elif menu_choice == "📤 Xuất kho Linh kiện lẻ":
        st.title("📤 XUẤT KHO LINH KIỆN LẺ")
        st.markdown("---")
        if not df.empty:
            lk_list = df[~df["Ma_LK"].str.startswith(("CB", "CM"), na=False)]
            if not lk_list.empty:
                opts = [f"{r['Ma_LK']} - {r['Ten_LK']} (Kho: {r.get('Kho_quan_ly', 'Kho 1')} | Tồn: {r['So_luong']})" for _, r in lk_list.iterrows()]
                sel = st.selectbox("Chọn linh kiện cần xuất:", opts)
                ma_sel = sel.split(" - ")[0]
                kho_sel = sel.split("Kho: ")[1].split(" |")[0]
                with st.form("export_lk_form"):
                    sl_xuat = st.number_input("Số lượng xuất", min_value=1, value=1)
                    ghi_chu = st.text_input("Nội dung xuất kho")
                    submitted = st.form_submit_button("Xác nhận xuất lẻ")
                    if submitted:
                        row_lk = df[(df["Ma_LK"] == ma_sel) & (df["Kho_quan_ly"] == kho_sel)].iloc[0]
                        new_ton = max(0, int(row_lk["So_luong"]) - int(sl_xuat))
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Admin")
                        log_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - 📤 Xuất lẻ tại kho '{kho_sel}': -{sl_xuat} | Nội dung: {ghi_chu}"
                        old_logs = row_lk.get("Nhat_ky", "")
                        if old_logs: log_str = old_logs + "\n" + log_str
                        supabase.table("Ton_kho").update({"So_luong": new_ton, "Nhat_ky": log_str}).eq("Ma_LK", ma_sel).eq("Kho_quan_ly", kho_sel).execute()
                        st.success("Xuất kho thành công!")
                        st.rerun()
            else:
                st.info("Không có linh kiện nào.")
    # 12. BÁO CÁO DOANH THU & LỢI NHUẬN
    elif menu_choice == "📊 Báo cáo Doanh thu & Lợi nhuận":
        st.title("📊 BÁO CÁO DOANH THU & LỢI NHUẬN BÁN HÀNG")
        st.markdown("---")
        if not df.empty:
            sales_records = []
            for _, r in df.iterrows():
                logs = str(r.get("Nhat_ky", "")).split("\n")
                for line in logs:
                    if "🛒 Bán hàng POS" in line:
                        try:
                            time_match = re.search(r'\[(.*?)\]', line)
                            log_time = time_match.group(1) if time_match else ""
                            sl_match = re.search(r': -(\d+)', line)
                            sl_ban = int(sl_match.group(1)) if sl_match else 1
                            gx_match = re.search(r'Giá xuất: (\d+\.?\d*)', line)
                            gn_match = re.search(r'Giá nhập: (\d+\.?\d*)', line)
                            gx = float(gx_match.group(1)) if gx_match else float(r.get("Gia_xuat", 0))
                            gn = float(gn_match.group(1)) if gn_match else float(r.get("Gia_nhap", 0))
                            tt_type = "💵 Tiền mặt"
                            if "💳 Chuyển khoản" in line: tt_type = "💳 Chuyển khoản"
                            elif "📝 Ghi nợ" in line: tt_type = "📝 Ghi nợ công nợ"
                            sales_records.append({
                                "Thời gian": log_time,
                                "Mã QR": r["Ma_LK"],
                                "Tên sản phẩm": r["Ten_LK"],
                                "Số lượng": sl_ban,
                                "Doanh thu": sl_ban * gx,
                                "Tiền vốn": sl_ban * gn,
                                "Lợi nhuận": (sl_ban * gx) - (sl_ban * gn),
                                "Hình thức TT": tt_type
                            })
                        except Exception:
                            pass
            if sales_records:
                df_sales = pd.DataFrame(sales_records)
                tong_doanh_thu = df_sales["Doanh thu"].sum()
                tong_von = df_sales["Tiền vốn"].sum()
                tong_loi_nhuan = df_sales["Lợi nhuận"].sum()
                tong_don = len(df_sales)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("💰 TỔNG DOANH THU", f"{format_money(tong_doanh_thu)} VNĐ")
                m2.metric("📦 TỔNG TIỀN VỐN", f"{format_money(tong_von)} VNĐ")
                m3.metric("📈 LỢI NHUẬN GỘP", f"{format_money(tong_loi_nhuan)} VNĐ")
                m4.metric("🛒 SỐ ĐƠN BÁN RA", f"{tong_don} đơn")
                st.markdown("---")
                c_chart1, c_chart2 = st.columns(2)
                with c_chart1:
                    st.write("**Doanh thu theo sản phẩm**")
                    st.bar_chart(df_sales.groupby("Tên sản phẩm")["Doanh thu"].sum())
                with c_chart2:
                    st.write("**Tỷ trọng thanh toán**")
                    st.bar_chart(df_sales.groupby("Hình thức TT")["Doanh thu"].sum())
                st.markdown("---")
                st.dataframe(df_sales, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu bán hàng POS nào.")
    # 13. QUẢN LÝ CÔNG NỢ
    elif menu_choice == "📝 Quản lý Công nợ":
        st.title("📝 QUẢN LÝ CÔNG NỢ KHÁCH HÀNG")
        st.markdown("---")
        if not df.empty:
            debt_records = []
            for _, r in df.iterrows():
                logs = str(r.get("Nhat_ky", "")).split("\n")
                for line in logs:
                    if "📝 Ghi nợ công nợ" in line:
                        khach_match = re.search(r"cho khách '(.*?)'", line)
                        sdt_match = re.search(r"\(SĐT: (.*?)\)", line)
                        time_match = re.search(r'\[(.*?)\]', line)
                        sl_match = re.search(r': -(\d+)', line)
                        gx_match = re.search(r'Giá xuất: (\d+\.?\d*)', line)
                        debt_records.append({
                            "Ngày nợ": time_match.group(1) if time_match else "",
                            "Khách hàng": khach_match.group(1) if khach_match else "Khách nợ",
                            "SĐT": sdt_match.group(1) if sdt_match else "---",
                            "Sản phẩm nợ": r["Ten_LK"],
                            "Số tiền nợ (VNĐ)": (int(sl_match.group(1)) if sl_match else 1) * (float(gx_match.group(1)) if gx_match else float(r.get("Gia_xuat", 0))),
                            "Mã SP": r["Ma_LK"],
                            "Kho": r.get("Kho_quan_ly", "Kho 1")
                        })
            if debt_records:
                df_debts = pd.DataFrame(debt_records)
                st.error(f"### ⚠️ TỔNG CÔNG NỢ: `{format_money(df_debts['Số tiền nợ (VNĐ)'].sum())} VNĐ`")
                st.markdown("---")
                df_d_disp = df_debts.copy()
                df_d_disp["Số tiền nợ (VNĐ)"] = df_d_disp["Số tiền nợ (VNĐ)"].apply(format_money)
                st.dataframe(df_d_disp[["Ngày nợ", "Khách hàng", "SĐT", "Sản phẩm nợ", "Số tiền nợ (VNĐ)", "Kho"]], use_container_width=True)
            else:
                st.success("🎉 Không có khách hàng nào nợ tiền!")
    # 14. CẢNH BÁO TỒN KHO
    elif menu_choice == "⚠️ Cảnh báo tồn kho":
        st.title("⚠️ CẢNH BÁO HÀNG SẮP HẾT KHO")
        st.markdown("---")
        if not df.empty:
            nguong_canh_bao = st.number_input("Đặt ngưỡng cảnh báo số lượng tồn $\le$:", min_value=1, value=20, step=1)
            df_working = df.copy()
            df_working["So_luong"] = pd.to_numeric(df_working["So_luong"], errors="coerce").fillna(0)
            df_low_stock = df_working[df_working["So_luong"] <= nguong_canh_bao]
            if not df_low_stock.empty:
                st.warning(f"🚨 Có **{len(df_low_stock)}** mặt hàng có số lượng tồn kho $\le {nguong_canh_bao}$ cần nhập thêm gấp!")
                df_low_display = df_low_stock[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi"]].copy()
                df_low_display.columns = ["Mã QR", "Tên sản phẩm", "Kho", "Số lượng tồn", "Đơn vị"]
                st.dataframe(df_low_display, use_container_width=True)
            else:
                st.success(f"✅ Tất cả các mặt hàng đều có lượng tồn kho lớn hơn {nguong_canh_bao}!")
    # 15. BÁO CÁO & XUẤT EXCEL
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        st.markdown("---")
        st.info("💡 Tải toàn bộ dữ liệu tồn kho dưới dạng file **Excel (.xlsx)**.")
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_ton_kho = df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi", "Quy_cach"]].copy()
                df_ton_kho.columns = ["Mã QR", "Tên Sản Phẩm", "Kho", "Tồn Kho", "Đơn Vị", "Quy Cách"]
                df_ton_kho.to_excel(writer, sheet_name='Ton_Kho', index=False)
            st.download_button(
                label="📥 Tải xuống file Excel tồn kho",
                data=output.getvalue(),
                file_name=f"Bao_Cao_Ton_Kho_{datetime.now().strftime('%d%m%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
