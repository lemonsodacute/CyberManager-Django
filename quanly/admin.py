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

# -----------------------------------------------------------------------------
# KHU VỰC 1: CÁC MODEL NỀN TẢNG
# -----------------------------------------------------------------------------

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    search_fields = ('tai_khoan__username',)

@admin.register(KhachHang)
class KhachHangAdmin(admin.ModelAdmin):
    list_display = ('tai_khoan', 'so_du')
    search_fields = ('tai_khoan__username',)
    readonly_fields = ('so_du',) # Số dư chỉ nên được thay đổi qua giao dịch

@admin.register(May)
class MayAdmin(admin.ModelAdmin):
    list_display = ('ten_may', 'loai_may', 'trang_thai')
    list_filter = ('trang_thai', 'loai_may')
    search_fields = ('ten_may',)

admin.site.register(LoaiMay)

# -----------------------------------------------------------------------------
# KHU VỰC 2: QUẢN LÝ MENU VÀ KHO
# -----------------------------------------------------------------------------

admin.site.register(DanhMucMenu)
@admin.register(NguyenLieu)
class NguyenLieuAdmin(admin.ModelAdmin):
    list_display = ('ten_nguyen_lieu', 'don_vi_tinh', 'so_luong_ton')
    # Dòng này là bắt buộc để autocomplete_fields hoạt động
    search_fields = ('ten_nguyen_lieu',) 

class DinhLuongInline(admin.TabularInline):
    model = DinhLuong
    extra = 1
    autocomplete_fields = ['nguyen_lieu']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('ten_mon', 'danh_muc', 'don_gia', 'is_available')
    list_filter = ('danh_muc', 'is_available')
    search_fields = ('ten_mon',)
    inlines = [DinhLuongInline]

admin.site.register(KhuyenMai)

# -----------------------------------------------------------------------------
# KHU VỰC 3: CA LÀM VIỆC
# -----------------------------------------------------------------------------

@admin.register(LoaiCa)
class LoaiCaAdmin(admin.ModelAdmin):
    list_display = ('ten_ca', 'gio_bat_dau', 'gio_ket_thuc')
    search_fields = ('ten_ca',)

class GiaoDichTaiChinhInline(admin.TabularInline):
    model = GiaoDichTaiChinh
    extra = 0
    fields = ('thoi_gian_giao_dich', 'loai_giao_dich', 'so_tien', 'khach_hang')
    readonly_fields = fields
    can_delete = False
    def has_add_permission(self, request, obj): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(CaLamViec)
class CaLamViecAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ngay_lam_viec', 'trang_thai', 'tien_mat_ban_dau', 'tong_doanh_thu_he_thong', 'chenh_lech')
    list_filter = ('trang_thai', 'loai_ca', 'ngay_lam_viec')
    search_fields = ('nhan_vien__tai_khoan__username',)
    readonly_fields = ('thoi_gian_bat_dau_thuc_te', 'thoi_gian_ket_thuc_thuc_te', 'tong_doanh_thu_he_thong', 'chenh_lech')
    inlines = [GiaoDichTaiChinhInline]

# -----------------------------------------------------------------------------
# KHU VỰC 4: CÁC MODEL VẬN HÀNH
# -----------------------------------------------------------------------------

class ChiTietDonHangInline(admin.TabularInline):
    model = ChiTietDonHang
    extra = 1
    autocomplete_fields = ['mon']
    readonly_fields = ('thanh_tien',)

@admin.register(DonHangDichVu)
class DonHangDichVuAdmin(admin.ModelAdmin):
    list_display = ('id', 'phien_su_dung', 'ca_lam_viec', 'da_thanh_toan', 'tong_tien')
    list_filter = ('da_thanh_toan', 'ca_lam_viec__nhan_vien')
    inlines = [ChiTietDonHangInline]

@admin.register(PhienSuDung)
class PhienSuDungAdmin(admin.ModelAdmin):
    list_display = ('id', 'may', 'trang_thai', 'hinh_thuc', 'khach_hang', 'thoi_gian_bat_dau')
    list_filter = ('trang_thai', 'hinh_thuc')
    search_fields = ('may__ten_may', 'khach_hang__tai_khoan__username')

@admin.register(HoaDon)
class HoaDonAdmin(admin.ModelAdmin):
    list_display = ('id', 'phien_su_dung', 'ca_lam_viec', 'da_thanh_toan', 'tong_cong')
    list_filter = ('da_thanh_toan', 'ca_lam_viec__nhan_vien')
    readonly_fields = ('phien_su_dung', 'ca_lam_viec', 'tong_tien_gio', 'tong_tien_dich_vu', 'tien_giam_gia', 'tong_cong')

# -----------------------------------------------------------------------------
# KHU VỰC 5: SỔ CÁI TÀI CHÍNH
# -----------------------------------------------------------------------------

@admin.register(GiaoDichTaiChinh)
class GiaoDichTaiChinhAdmin(admin.ModelAdmin):
    list_display = ('thoi_gian_giao_dich', 'loai_giao_dich', 'so_tien', 'ca_lam_viec', 'khach_hang', 'hoa_don')
    list_filter = ('loai_giao_dich', 'ca_lam_viec__nhan_vien')
    
    # Bảo vệ dữ liệu
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False