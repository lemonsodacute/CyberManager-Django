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
    GiaoDichTaiChinh,
    # Kho & Kiểm Kê (Bổ sung)
    PhieuKiemKe, ChiTietKiemKe, LichSuThayDoiKho
)

# -----------------------------------------------------------------------------
# KHU VỰC 1: CÁC MODEL NỀN TẢNG
# -----------------------------------------------------------------------------

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    list_display = ['tai_khoan']
    search_fields = ['tai_khoan__username']


@admin.register(LoaiMay)
class LoaiMayAdmin(admin.ModelAdmin):
    list_display = ('ten_loai', 'don_gia_gio')
    search_fields = ('ten_loai',)# quanly/admin.py

# ... (các import và các class Admin khác)

@admin.register(KhachHang)
class KhachHangAdmin(admin.ModelAdmin):
    # <<< SỬA LỖI TẠI ĐÂY >>>
    # Hiển thị các trường từ model liên quan (tai_khoan) và của chính nó
    list_display = ['get_username', 'so_du'] 
    
    # Các trường chỉ đọc
    readonly_fields = ['get_username']
    
    # Thêm trường tìm kiếm cho tiện
    search_fields = ['tai_khoan__username']

    # Tạo một phương thức để lấy username từ model User liên quan
    @admin.display(description='Tên đăng nhập', ordering='tai_khoan__username')
    def get_username(self, obj):
        return obj.tai_khoan.username

@admin.register(May)
class MayAdmin(admin.ModelAdmin):
    list_display = ('ten_may', 'loai_may', 'trang_thai')
    list_filter = ('trang_thai', 'loai_may')
    search_fields = ('ten_may',)

# -----------------------------------------------------------------------------
# KHU VỰC 2: QUẢN LÝ MENU VÀ KHO
# -----------------------------------------------------------------------------

@admin.register(DanhMucMenu)
class DanhMucMenuAdmin(admin.ModelAdmin):
    search_fields = ('ten_danh_muc',)

@admin.register(NguyenLieu)
class NguyenLieuAdmin(admin.ModelAdmin):
    list_display = ('ten_nguyen_lieu', 'don_vi_tinh', 'so_luong_ton')
    search_fields = ('ten_nguyen_lieu',)

class DinhLuongInline(admin.TabularInline):
    model = DinhLuong
    extra = 1
    autocomplete_fields = ['nguyen_lieu']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    inlines = [DinhLuongInline]
    list_display = ('ten_mon', 'danh_muc', 'don_gia', 'is_available')
    list_filter = ('danh_muc', 'is_available')
    search_fields = ('ten_mon',)

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
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

# -----------------------------------------------------------------------------
# KHU VỰC 6: QUẢN LÝ KHO VÀ KIỂM KÊ (Bổ sung)
# -----------------------------------------------------------------------------

class ChiTietKiemKeInline(admin.TabularInline):
    model = ChiTietKiemKe
    extra = 0
    readonly_fields = ('nguyen_lieu', 'ton_he_thong', 'ton_thuc_te', 'chenh_lech')
    can_delete = False
    def has_add_permission(self, request, obj): return False

@admin.register(PhieuKiemKe)
class PhieuKiemKeAdmin(admin.ModelAdmin):
    list_display = ('id', 'ca_lam_viec', 'nhan_vien', 'thoi_gian_tao', 'da_xac_nhan')
    list_filter = ('da_xac_nhan',)
    inlines = [ChiTietKiemKeInline]
    # Thêm action để admin xác nhận phiếu
    actions = ['xac_nhan_va_cap_nhat_kho']

    @admin.action(description='Xác nhận và Cập nhật kho từ các phiếu đã chọn')
    def xac_nhan_va_cap_nhat_kho(self, request, queryset):
        # ... (logic xử lý xác nhận phiếu sẽ được viết ở đây)
        self.message_user(request, "Chức năng đang được phát triển.")

@admin.register(LichSuThayDoiKho)
class LichSuThayDoiKhoAdmin(admin.ModelAdmin):
    list_display = ('thoi_gian', 'nguyen_lieu', 'so_luong_thay_doi', 'loai_thay_doi', 'nhan_vien')
    list_filter = ('loai_thay_doi', 'nhan_vien')
    # Bảo vệ dữ liệu
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False