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
# --- MENU BÊN TRÁI ---
st.sidebar.title(f"👤 Xin chào: {st.session_state.username}")
st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Danh Mục Quản Lý")
menu_choice = st.sidebar.radio(
    "Chọn chức năng:",
    [
        "🛍️ Bán hàng & In hóa đơn (POS)",
        "📊 Báo cáo Doanh thu & Lợi nhuận",
        "📝 Quản lý Công nợ",
        "⚠️ Cảnh báo tồn kho",
        "📦 Tổng quan tồn kho", 
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
                                # Lưu thông tin hóa đơn vừa thanh toán để in
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
        # GIAO DIỆN IN HÓA ĐƠN KHI THANH TOÁN XONG
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
    # 2. BÁO CÁO DOANH THU & LỢI NHUẬN
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
                # Tổng quan dạng số
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
                st.subheader("📉 Biểu Đồ Thống Kê")
                c_chart1, c_chart2 = st.columns(2)
                with c_chart1:
                    st.write("**Doanh thu & Lợi nhuận theo sản phẩm**")
                    chart_data = df_sales.groupby("Tên sản phẩm")[["Doanh thu", "Lợi nhuận"]].sum()
                    st.bar_chart(chart_data)
                with c_chart2:
                    st.write("**Tỷ trọng hình thức thanh toán**")
                    tt_data = df_sales.groupby("Hình thức TT")["Doanh thu"].sum()
                    st.bar_chart(tt_data)
                st.markdown("---")
                st.subheader("📋 Chi tiết danh sách lịch sử bán hàng")
                st.dataframe(df_sales, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu bán hàng POS nào được ghi nhận.")
    # 3. QUẢN LÝ CÔNG NỢ KHÁCH HÀNG
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
                        ten_k = khach_match.group(1) if khach_match else "Khách nợ"
                        sdt_k = sdt_match.group(1) if sdt_match else "---"
                        t_k = time_match.group(1) if time_match else ""
                        sl = int(sl_match.group(1)) if sl_match else 1
                        gx = float(gx_match.group(1)) if gx_match else float(r.get("Gia_xuat", 0))
                        debt_records.append({
                            "Ngày nợ": t_k,
                            "Khách hàng": ten_k,
                            "SĐT": sdt_k,
                            "Sản phẩm nợ": r["Ten_LK"],
                            "Số tiền nợ (VNĐ)": sl * gx,
                            "Mã SP": r["Ma_LK"],
                            "Kho": r.get("Kho_quan_ly", "Kho 1")
                        })
            if debt_records:
                df_debts = pd.DataFrame(debt_records)
                tong_cong_no = df_debts["Số tiền nợ (VNĐ)"].sum()
                st.error(f"### ⚠️ TỔNG CÔNG NỢ KHÁCH ĐANG NỢ: `{format_money(tong_cong_no)} VNĐ`")
                st.markdown("---")
                df_debts_display = df_debts.copy()
                df_debts_display["Số tiền nợ (VNĐ)"] = df_debts_display["Số tiền nợ (VNĐ)"].apply(format_money)
                st.dataframe(df_debts_display[["Ngày nợ", "Khách hàng", "SĐT", "Sản phẩm nợ", "Số tiền nợ (VNĐ)", "Kho"]], use_container_width=True)
                st.markdown("---")
                st.subheader("🤝 Gạch nợ / Xóa nợ khi khách thanh toán")
                with st.form("pay_debt_form"):
                    selected_debt_idx = st.selectbox("Chọn khoản nợ khách đã thanh toán:", range(len(debt_records)), format_func=lambda i: f"{debt_records[i]['Khách hàng']} - {debt_records[i]['Sản phẩm nợ']} ({format_money(debt_records[i]['Số tiền nợ (VNĐ)'])}đ)")
                    btn_pay = st.form_submit_button("✅ XÁC NHẬN ĐÃ THU NỢ")
                    if btn_pay:
                        target = debt_records[selected_debt_idx]
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        db_m = df[(df["Ma_LK"] == target["Mã SP"]) & (df["Kho_quan_ly"] == target["Kho"])]
                        if not db_m.empty:
                            old_l = db_m.iloc[0].get("Nhat_ky", "")
                            new_l = old_l.replace("📝 Ghi nợ công nợ", "✅ Đã thu xong nợ")
                            supabase.table("Ton_kho").update({"Nhat_ky": new_l}).eq("Ma_LK", target["Mã SP"]).eq("Kho_quan_ly", target["Kho"]).execute()
                            st.success("Đã cập nhật gạch nợ thành công!")
                            st.rerun()
            else:
                st.success("🎉 Hiện tại không có khách hàng nào nợ tiền!")
    # 4. CẢNH BÁO TỒN KHO THẤP
    elif menu_choice == "⚠️ Cảnh báo tồn kho":
        st.title("⚠️ CẢNH BÁO HÀNG SẮP HẾT KHO")
        st.markdown("---")
        if not df.empty:
            nguong_canh_bao = st.number_input("Đặt ngưỡng cảnh báo số lượng tồn $\le$:", min_value=1, value=5, step=1)
            df_working = df.copy()
            df_working["So_luong"] = pd.to_numeric(df_working["So_luong"], errors="coerce").fillna(0)
            df_low_stock = df_working[df_working["So_luong"] <= nguong_canh_bao]
            if not df_low_stock.empty:
                st.warning(f"🚨 Có **{len(df_low_stock)}** mặt hàng sắp hết kho cần nhập thêm gấp!")
                df_low_display = df_low_stock[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi"]].copy()
                df_low_display.columns = ["Mã QR", "Tên sản phẩm", "Kho", "Số lượng tồn", "Đơn vị"]
                st.dataframe(df_low_display, use_container_width=True)
            else:
                st.success("✅ Tất cả các mặt hàng đều đang có lượng tồn kho an toàn!")
    # CÁC MỤC KHÁC GIỮ NGUYÊN CODE CŨ
    elif menu_choice == "📊 Tổng quan tồn kho":
        st.title("📦 TỒN KHO HỆ THỐNG")
        st.dataframe(df[["Ma_LK", "Ten_LK", "Kho_quan_ly", "So_luong", "Don_vi"]], use_container_width=True)
    elif menu_choice == "🔍 Tra cứu & Lọc chi tiết":
        st.title("🔍 TRA CỨU & LỌC CHI TIẾT")
        st.dataframe(df, use_container_width=True)
    elif menu_choice == "📈 Báo cáo & Xuất Excel":
        st.title("📈 Báo Cáo Kho & Xuất File Excel")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Ton_Kho', index=False)
        st.download_button("📥 Tải file Excel", data=output.getvalue(), file_name="Bao_Cao_Ton_Kho.xlsx")
