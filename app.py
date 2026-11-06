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
# Hàm loại bỏ dấu tiếng Việt
def remove_vietnamese_accent(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.replace('đ', 'd').replace('Đ', 'D')
    return text
# Hàm tự động sinh mã chuẩn gọn gàng, tối ưu cho kế toán & kho vận
def generate_code_from_name(full_name, is_combo=False, item_type="VT"):
    if not full_name or not full_name.strip():
        return ""
    clean_no_accent = remove_vietnamese_accent(full_name.strip())
    upper_name = clean_no_accent.upper()
    if is_combo:
        clean_code = re.sub(r'[^A-Z0-9]', '_', upper_name)
        clean_code = re.sub(r'_+', '_', clean_code).strip('_')
        parts = clean_code.split('_')
        short_str = "_".join(parts[:3]) if len(parts) > 3 else clean_code
        return f"CB-{short_str[:20]}"
    prefix = item_type if item_type in ["LK", "VT"] else "VT"
    # Viết tắt các từ khóa thông dụng để mã gọn gàng
    upper_name = upper_name.replace("BULONG", "BL").replace("BU LONG", "BL")
    upper_name = upper_name.replace("LONG DEN", "LD").replace("LON DEN", "LD")
    clean_code = re.sub(r'[^A-Z0-9]', '_', upper_name)
    clean_code = re.sub(r'_+', '_', clean_code).strip('_')
    auto_code = f"{prefix}-{clean_code[:22]}"
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
                            sub_dv = tp.get('dv', 'Cái')
                            sub_img = tp.get('img', '')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            if not sub_name and not sub_match.empty:
                                sub_name = sub_match.iloc[0]["Ten_LK"]
                            st.write(f"- `{sub_m}` ({sub_name}) | Định mức: **{sub_sl} {sub_dv}**")
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
        st.info("📖 **HƯỚNG DẪN NGUYÊN TẮC TẠO MÃ COMBO:**\n"
                  "- **Cấu trúc mã chuẩn:** `CB-[Tên_Viết_Tắt]`\n"
                  "- **Ví dụ:** Combo tên *'Bộ bàn gỗ lim'* ➡️ Hệ thống tự sinh mã gọn: `CB-BO_BAN_GO_LIM`\n"
                  "- ⚠️ **Lưu ý:** Nếu mã trùng với hệ thống, màn hình sẽ hiển thị **cảnh báo đỏ** để bạn kiểm tra lại.")
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
            ten_lk = st.text_input("Tên Combo", value=def_ten, key="cb_ten_input", placeholder="VD: Bộ bàn gỗ lim")
            auto_cb_code = generate_code_from_name(ten_lk, is_combo=True)
            cb_ma_mode = st.radio(
                "Phương thức mã Combo:",
                ["🤖 Tự sinh", "✍️ Tự viết"],
                horizontal=True,
                key="cb_ma_mode_radio"
            )
            if cb_ma_mode.startswith("🤖"):
                ma_lk = st.text_input("Mã Combo (mã tự động từ hệ thống)", value=auto_cb_code, key="cb_code_auto_val")
            else:
                ma_lk = st.text_input("Mã Combo (Cá nhân tự viết)", value=def_ma if def_ma else auto_cb_code, key="cb_code_manual_val")
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
