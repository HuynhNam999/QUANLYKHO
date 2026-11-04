# PHẦN MỀM QUẢN LÝ TỒN KHO & BÓC TÁCH BOM COMBO
print("==========================================")
print("   CHƯƠNG TRÌNH QUẢN LÝ TỒN KHO TỰ ĐỘNG    ")
print("==========================================\n")

# 1. Định nghĩa danh mục linh kiện / vật tư lẻ trong kho
# (Tương ứng với dữ liệu nguồn linh kiện)
kho_linh_kien = {
    "LK-MATBAN-01": {"ten": "Mặt bàn gỗ sồi 1m2", "ton_dau": 100, "nhap": 50, "xuat": 20},
    "LK-THANBAN01": {"ten": "Thân bàn gỗ", "ton_dau": 100, "nhap": 60, "xuat": 30},
    "VT-DINH-01": {"ten": "Đinh vít 5cm", "ton_dau": 1000, "nhap": 500, "xuat": 200}
}

# 2. Định nghĩa định mức BOM của Combo (SET)
# Ví dụ: 1 bộ SET-BANGO-01 cần 1 Mặt bàn, 1 Thân bàn và 4 Đinh vít
dinh_muc_combo = {
    "SET-BANGO-01": [
        {"ma_lk": "LK-MATBAN-01", "so_luong": 1},
        {"ma_lk": "LK-THANBAN01", "so_luong": 1},
        {"ma_lk": "VT-DINH-01", "so_luong": 4}
    ]
}

print("--- 1. BẢNG ĐỊNH MỨC BOM COMBO ---")
for ma_combo, ds_lk in dinh_muc_combo.items():
    print(f"Mã Combo: {ma_combo}")
    for item in ds_lk:
        print(f"   -> Cần {item['so_luong']} linh kiện [{item['ma_lk']}]")

print("\n--- 2. TÍNH TOÁN TỒN KHO TỰ ĐỘNG (ĐÃ BÓC TÁCH COMBO) ---")
# Giả sử trong kỳ có phát sinh xuất kho combo: xuất 10 bộ SET-BANGO-01
so_luong_xuat_combo = 10
print(f"Phát sinh: Xuất bán {so_luong_xuat_combo} bộ [{list(dinh_muc_combo.keys())[0]}]")

# Tự động bóc tách trừ kho linh kiện lẻ cấu thành combo (giống logic công thức SUMPRODUCT trong Sheets)
for item in dinh_muc_combo["SET-BANGO-01"]:
    ma_lk = item['ma_lk']
    sl_tieu_hao = item['so_luong'] * so_luong_xuat_combo
    # Cộng dồn số lượng xuất do bóc tách combo vào kho linh kiện
    kho_linh_kien[ma_lk]["xuat"] += sl_tieu_hao

print("\n--- 3. BẢNG TỒN KHO CUỐI KỲ (BÁO CÁO) ---")
print(f"{'Mã Linh Kiện':<15} | {'Tên Linh Kiện':<20} | {'Tồn Đầu':<10} | {'Tổng Nhập':<10} | {'Tổng Xuất':<10} | {'Tồn Cuối':<10}")
print("-" * 85)

for ma_lk, thong_tin in kho_linh_kien.items():
    ton_cuoi = thong_tin["ton_dau"] + thong_tin["nhap"] - thong_tin["xuat"]
    print(f"{ma_lk:<15} | {thong_tin['ten']:<20} | {thong_tin['ton_dau']:<10} | {thong_tin['nhap']:<10} | {thong_tin['xuat']:<10} | {ton_cuoi:<10}")

print("\n=> Hoàn tất mô phỏng logic tự động bóc tách BOM combo thành công!")