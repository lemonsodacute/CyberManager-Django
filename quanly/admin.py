# quanly/admin.py

from django.contrib import admin
from .models import (
    # Nền tảng
    NhanVien, KhachHang, LoaiMay, May,
    
    # Menu & Kho
    DanhMucMenu, NguyenLieu, MenuItem, DinhLuong,
    
    # Ca làm việc & Vận hành
    LoaiCa, CaLamViec, PhienSuDung, DonHangDichVu, 
    ChiTietDonHang, KhuyenMai, HoaDon,
    
    # Tài chính
    GiaoDichTaiChinh
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
    list_display = ('thoi_gian_giao_dich', 'loai_giao_dich', 'so_tien', 'ca_lam_viec')
    list_filter = ('loai_giao_dich',)


# Đăng ký các model còn lại không cần tùy chỉnh nhiều
admin.site.register(LoaiMay)
admin.site.register(DanhMucMenu)
admin.site.register(NguyenLieu)
admin.site.register(DonHangDichVu)
admin.site.register(KhuyenMai)
admin.site.register(LoaiCa)