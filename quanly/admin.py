# quanly/admin.py

<<<<<<< HEAD
from django.contrib import admin, messages
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from .models import (
    NhanVien, KhachHang, LoaiMay, May,
    DanhMucMenu, NguyenLieu, MenuItem,
    PhieuNhapKho, ChiTietNhapKho,
    PhienSuDung, DonHangDichVu, ChiTietDonHang, HoaDon,
    GiaoDichTaiChinh,
    LoaiCa, CaLamViec  # <-- THÊM LoaiCa VÀ CaLamViec VÀO ĐÂY
)


# --- ĐĂNG KÝ CÁC MODEL ---

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    search_fields = ('tai_khoan__username',)

@admin.register(KhachHang)
class KhachHangAdmin(admin.ModelAdmin):
    list_display = ('tai_khoan', 'so_du')
    search_fields = ('tai_khoan__username',)

@admin.register(May)
class MayAdmin(admin.ModelAdmin):
    list_display = ('ten_may', 'loai_may', 'trang_thai')
    list_filter = ('trang_thai', 'loai_may')
    search_fields = ('ten_may',)

class DinhLuongInline(admin.TabularInline):
    model = DinhLuong
    extra = 1

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('ten_mon', 'danh_muc', 'don_gia', 'is_available')
    list_filter = ('danh_muc', 'is_available')
    inlines = [DinhLuongInline]

@admin.register(CaLamViec)
class CaLamViecAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'trang_thai')
    list_filter = ('trang_thai', 'nhan_vien', 'loai_ca', 'ngay_lam_viec')

@admin.register(PhienSuDung)
class PhienSuDungAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'trang_thai', 'hinh_thuc')
    list_filter = ('trang_thai', 'hinh_thuc')

@admin.register(HoaDon)
class HoaDonAdmin(admin.ModelAdmin):
    list_display = ('id', 'phien_su_dung', 'ca_lam_viec', 'da_thanh_toan', 'tong_cong')
    list_filter = ('da_thanh_toan',)

@admin.register(GiaoDichTaiChinh)
class GiaoDichTaiChinhAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = ('thoi_gian_giao_dich', 'loai_giao_dich', 'so_tien', 'nhan_vien_thuc_hien', 'khach_hang')
    list_filter = ('loai_giao_dich', 'nhan_vien_thuc_hien')
    readonly_fields = [f.name for f in GiaoDichTaiChinh._meta.fields]
    
    
@admin.register(LoaiCa)
class LoaiCaAdmin(admin.ModelAdmin):
    # --- THAY ĐỔI ---
    # Hiển thị các cột mới thay vì chỉ mô tả
    list_display = ('ten_ca', 'gio_bat_dau', 'gio_ket_thuc', 'mo_ta')
    search_fields = ('ten_ca',)

@admin.register(CaLamViec)
class CaLamViecAdmin(admin.ModelAdmin):
    list_display = ('nhan_vien', 'loai_ca', 'thoi_gian_bat_dau_thuc_te', 'thoi_gian_ket_thuc_thuc_te', 'trang_thai')
    list_filter = ('trang_thai', 'loai_ca')
    search_fields = ('nhan_vien__tai_khoan__username',)
    raw_id_fields = ('nhan_vien', 'loai_ca') # Giúp chọn FK dễ hơn nếu có nhiều NV/LoaiCa
=======
    list_display = ('thoi_gian_giao_dich', 'loai_giao_dich', 'so_tien', 'ca_lam_viec')
    list_filter = ('loai_giao_dich',)


# Đăng ký các model còn lại không cần tùy chỉnh nhiều
admin.site.register(LoaiMay)
admin.site.register(DanhMucMenu)
admin.site.register(NguyenLieu)
admin.site.register(DonHangDichVu)
admin.site.register(KhuyenMai)
admin.site.register(LoaiCa)
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
