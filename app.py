import streamlit as st
import pandas as pd

st.set_page_config(page_title="Phần Mềm Quản Lý Tồn Kho", layout="wide")

st.title("📦 PHẦN MỀM QUẢN LÝ TỒN KHO & BÓC TÁCH BOM COMBO")
st.write("Giao diện quản lý tự động vận hành trên nền tảng Python")

# 1. Dữ liệu giả lập
if 'kho' not in st.session_state:
    st.session_state.kho = {
        "LK-MATBAN-01": {"ten": "Mặt bàn gỗ sồi 1m2", "ton_dau": 100, "nhap": 50, "xuat": 20},
        "LK-THANBAN01": {"ten": "Thân bàn gỗ", "ton_dau": 100, "nhap": 60, "xuat": 30},
        "VT-DINH-01": {"ten": "Đinh vít 5cm", "ton_dau": 1000, "nhap": 500, "xuat": 200}
    }

dinh_muc_combo = {
    "SET-BANGO-01": [
        {"ma_lk": "LK-MATBAN-01", "so_luong": 1},
        {"ma_lk": "LK-THANBAN01", "so_luong": 1},
        {"ma_lk": "VT-DINH-01", "so_luong": 4}
    ]
}

# 2. Tạo các Tab chức năng
tab1, tab2, tab3 = st.tabs(["📊 Báo Cáo Tồn Kho", "📤 Xuất Kho Combo (BOM)", "📋 Định Mức BOM"])

with tab1:
    st.subheader("Bảng Báo Cáo Tồn Kho Hiện Tại")
    data = []
    for ma_lk, info in st.session_state.kho.items():
        ton_cuoi = info["ton_dau"] + info["nhap"] - info["xuat"]
        data.append({
            "Mã Linh Kiện": ma_lk,
            "Tên Linh Kiện": info["ten"],
            "Tồn Đầu": info["ton_dau"],
            "Tổng Nhập": info["nhap"],
            "Tổng Xuất": info["xuat"],
            "Tồn Cuối Kỳ": ton_cuoi
        })
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Thực Hiện Xuất Kho Theo Mã Combo")
    col1, col2 = st.columns(2)
    with col1:
        combo_chon = st.selectbox("Chọn Mã Combo Xuất Kho:", list(dinh_muc_combo.keys()))
        so_luong_xuat = st.number_input("Số Lượng Combo Xuất:", min_value=1, value=1, step=1)
        
        if st.button("🚀 Thực Hiện Trừ Kho BOM"):
            for item in dinh_muc_combo[combo_chon]:
                ma_lk = item["ma_lk"]
                sl_tru = item["so_luong"] * so_luong_xuat
                st.session_state.kho[ma_lk]["xuat"] += sl_tru
            st.success(f"Đã xuất thành công {so_luong_xuat} bộ {combo_chon} và tự động trừ kho linh kiện lẻ!")

with tab3:
    st.subheader("Chi Tiết Định Mức BOM")
    for combo, ds in dinh_muc_combo.items():
        st.write(f"**Combo: {combo}**")
        st.table(pd.DataFrame(ds))