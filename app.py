import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client
import json
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
# --- MENU ĐIỀU HƯỚNG BÊN TRÁI RÕ RÀNG TỪNG CHỨC NĂNG ---
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
        "📤 Xuất kho Combo", 
        "📤 Xuất kho Linh kiện lẻ"
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
            def highlight_negative(val):
                color = 'red' if isinstance(val, (int, float)) and val < 0 else 'black'
                return f'color: {color}; text-align: center;'
            df_display = df[["Ma_LK", "Ten_LK", "So_luong", "Don_vi", "Nhat_ky"]]
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
                            sub_sl = tp.get('sl')
                            sub_match = df[df["Ma_LK"] == sub_m]
                            sub_name = sub_match.iloc[0]["Ten_LK"] if not sub_match.empty else ""
                            st.write(f"- `{sub_m}` ({sub_name}) | Định mức trong bộ: **{sub_sl}**")
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
    # 3. NHẬP MỚI COMBO (Phần 2 chọn từ danh sách có sẵn để tuyệt đối khớp Mã và Tên)
    elif menu_choice == "📥 Nhập mới Combo":
        st.title("📦 KHAI BÁO & NHẬP MỚI COMBO SẢN PHẨM")
        st.markdown("---")
        with st.form("add_combo_form", clear_on_submit=True):
            st.markdown("### 🏷️ PHẦN 1: THÔNG TIN COMBO (Mã bắt đầu bằng CB-...)")
            c1, c2 = st.columns(2)
            with c1:
                ma_lk = st.text_input("Mã Combo (VD: CB-MVRS-01)")
                ten_lk = st.text_input("Tên Combo (VD: Bộ cánh quạt xe máy)")
                so_luong = st.number_input("Số lượng bộ ban đầu", min_value=0, step=1)
            with c2:
                don_vi = st.selectbox("Đơn vị tính", ["Bộ", "Hộp", "Combo"])
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")
            ghi_chu_tay = st.text_input("Ghi chú thêm", placeholder="Ví dụ: Nhập kho bộ combo mới")
            st.markdown("---")
            st.markdown("### 🧩 PHẦN 2: KHAI BÁO THÀNH PHẦN TRONG COMBO (Chọn chính xác từ danh sách LK/VT đã có)")
            st.info("💡 Hệ thống tự động gợi ý danh sách mã và tên linh kiện/vật tư đã khai báo trước đó để tránh việc gõ sai tên lệch mã.")
            options_list = ["Không chọn"]
            code_map = {}
            if not df.empty:
                for _, row in df.iterrows():
                    display_str = f"{row['Ma_LK']} - {row['Ten_LK']}"
                    options_list.append(display_str)
                    code_map[display_str] = row['Ma_LK']
            # 10 linh kiện / vật tư thành phần (Chọn từ selectbox để đồng bộ tuyệt đối mã và tên)
            sc1, sc2 = st.columns(2)
            with sc1:
                tp1_opt = st.selectbox("Thành phần 1 (Chọn LK/VT)", options_list, key="tp1_o")
                tp1_sl = st.number_input("Định mức SL thành phần 1", min_value=1, value=1, key="tp1_s")
            with sc2:
                tp2_opt = st.selectbox("Thành phần 2 (Chọn LK/VT)", options_list, key="tp2_o")
                tp2_sl = st.number_input("Định mức SL thành phần 2", min_value=1, value=1, key="tp2_s")
            sc3, sc4 = st.columns(2)
            with sc3:
                tp3_opt = st.selectbox("Thành phần 3 (Chọn LK/VT)", options_list, key="tp3_o")
                tp3_sl = st.number_input("Định mức SL thành phần 3", min_value=1, value=1, key="tp3_s")
            with sc4:
                tp4_opt = st.selectbox("Thành phần 4 (Chọn LK/VT)", options_list, key="tp4_o")
                tp4_sl = st.number_input("Định mức SL thành phần 4", min_value=1, value=1, key="tp4_s")
            sc5, sc6 = st.columns(2)
            with sc5:
                tp5_opt = st.selectbox("Thành phần 5 (Chọn LK/VT)", options_list, key="tp5_o")
                tp5_sl = st.number_input("Định mức SL thành phần 5", min_value=1, value=1, key="tp5_s")
            with sc6:
                tp6_opt = st.selectbox("Thành phần 6 (Chọn LK/VT)", options_list, key="tp6_o")
                tp6_sl = st.number_input("Định mức SL thành phần 6", min_value=1, value=1, key="tp6_s")
            sc7, sc8 = st.columns(2)
            with sc7:
                tp7_opt = st.selectbox("Thành phần 7 (Chọn LK/VT)", options_list, key="tp7_o")
                tp7_sl = st.number_input("Định mức SL thành phần 7", min_value=1, value=1, key="tp7_s")
            with sc8:
                tp8_opt = st.selectbox("Thành phần 8 (Chọn LK/VT)", options_list, key="tp8_o")
                tp8_sl = st.number_input("Định mức SL thành phần 8", min_value=1, value=1, key="tp8_s")
            sc9, sc10 = st.columns(2)
            with sc9:
                tp9_opt = st.selectbox("Thành phần 9 (Chọn LK/VT)", options_list, key="tp9_o")
                tp9_sl = st.number_input("Định mức SL thành phần 9", min_value=1, value=1, key="tp9_s")
            with sc10:
                tp10_opt = st.selectbox("Thành phần 10 (Chọn LK/VT)", options_list, key="tp10_o")
                tp10_sl = st.number_input("Định mức SL thành phần 10", min_value=1, value=1, key="tp10_s")
            danh_sach_thanh_phan = []
            tps = [
                (tp1_opt, tp1_sl), (tp2_opt, tp2_sl), (tp3_opt, tp3_sl), (tp4_opt, tp4_sl), (tp5_opt, tp5_sl),
                (tp6_opt, tp6_sl), (tp7_opt, tp7_sl), (tp8_opt, tp8_sl), (tp9_opt, tp9_sl), (tp10_opt, tp10_sl)
            ]
            for opt, sl in tps:
                if opt != "Không chọn":
                    danh_sach_thanh_phan.append({"ma": code_map[opt], "sl": int(sl)})
            save_btn = st.form_submit_button("💾 Lưu Combo vào Database")
            if save_btn:
                if ma_lk and ten_lk:
                    try:
                        ngay_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M")
                        nguoi_thuc_hien = st.session_state.get("username", "Hệ thống")
                        nhat_ky_str = f"[{ngay_hien_tai}] 👤 {nguoi_thuc_hien} - {loai_gd}: {so_luong} {don_vi}"
                        if ghi_chu_tay:
                            nhat_ky_str += f" | Ghi chú: {ghi_chu_tay}"
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
                        st.success("Đã lưu Combo thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên Combo!")
    # 4. NHẬP MỚI LINH KIỆN LẺ
    elif menu_choice == "📥 Nhập mới Linh kiện lẻ":
        st.title("🔩 KHAI BÁO & NHẬP MỚI LINH KIỆN / VẬT TƯ LẺ")
        st.markdown("---")
        st.info("💡 Quy tắc mã linh kiện / vật tư lẻ nên bắt đầu bằng tiền tố **LK-** hoặc **VT-** (Ví dụ: `LK-CANHQUAT-01`, `VT-OCVIT-05`).")
        with st.form("add_item_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ma_lk = st.text_input("Mã LK / VT (VD: LK-CANHQUAT-01)")
                ten_lk = st.text_input("Tên linh kiện / vật tư (VD: Cánh quạt nhựa)")
                so_luong = st.number_input("Số lượng tồn kho ban đầu", min_value=0, step=1)
            with c2:
                don_vi = st.selectbox("Đơn vị tính", ["Cái", "Chiếc", "Túi", "Cuộn", "Hộp", "Kg", "Mét"])
                loai_gd = st.selectbox("Loại thao tác", ["📥 Nhập kho mới", "🔄 Cập nhật thông tin"])
                hinh_anh = st.text_input("Link ảnh chi tiết (URL công khai)")
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
                        new_data = {
                            "Ma_LK": ma_lk,
                            "Ten_LK": ten_lk,
                            "So_luong": int(so_luong),
                            "Don_vi": don_vi,
                            "Nhat_ky": nhat_ky_str,
                            "Hinh_anh": hinh_anh,
                            "Thanh_phan": []
                        }
                        supabase.table("Ton_kho").upsert(new_data).execute()
                        st.success("Đã lưu linh kiện/vật tư lẻ thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi lưu dữ liệu: {e}")
                else:
                    st.warning("Vui lòng điền đầy đủ Mã và Tên linh kiện/vật tư!")
    # 5. XUẤT KHO COMBO
    elif menu_choice == "📤 Xuất kho Combo":
        st.title("📤 XUẤT KHO COMBO (Tự động trừ định mức linh kiện/vật tư con)")
        st.markdown("---")
        if not df.empty:
            combo_df = df[df["Ma_LK"].str.startswith("CB", na=False)]
            if combo_df.empty:
                combo_df = df
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
                    sub_item = df[df["Ma_LK"] == sub_m]
                    sub_name = sub_item.iloc[0]["Ten_LK"] if not sub_item.empty else "Không rõ"
                    sub_stock = sub_item.iloc[0]["So_luong"] if not sub_item.empty else 0
                    st.write(f"- `{sub_m}` ({sub_name}) | Định mức trừ: **{tp.get('sl')} x SL xuất** | Tồn kho hiện tại: `{sub_stock}`")
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
            st.warning("Kho hiện đang trống!")
    # 6. XUẤT KHO LINH KIỆN LẺ
    elif menu_choice == "📤 Xuất kho Linh kiện lẻ":
        st.title("📤 XUẤT KHO LINH KIỆN / VẬT TƯ LẺ (Độc lập)")
        st.markdown("---")
        if not df.empty:
            export_options = [f"{row['Ma_LK']} - {row['Ten_LK']}" for _, row in df.iterrows()]
            selected_export_opt = st.selectbox("1️⃣ Chọn linh kiện / vật tư cần xuất kho", export_options)
            selected_export_item = selected_export_opt.split(" - ")[0]
            current_item_row = df[df["Ma_LK"] == selected_export_item].iloc[0]
            hien_thi_ten = current_item_row["Ten_LK"]
            ton_hien_tai = current_item_row["So_luong"]
            don_vi_tinh = current_item_row["Don_vi"]
            hinh_anh_cu = current_item_row["Hinh_anh"]
            thanh_phan_list = current_item_row.get("Thanh_phan", [])
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
                        st.success(f"Xuất linh kiện/vật tư lẻ thành công! Tồn kho mới còn lại: {so_luong_moi} {don_vi_tinh}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi thực hiện xuất kho: {e}")
        else:
            st.warning("Kho hiện đang trống!")
