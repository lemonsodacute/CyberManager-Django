# quanly/admin.py

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

# ... (Các lớp Admin cho Kho & Menu giữ nguyên như file trước) ...
# KHU VỰC 1: CÁC MODEL NỀN TẢNG
admin.site.register(NhanVien)
admin.site.register(KhachHang)
admin.site.register(LoaiMay)
admin.site.register(DanhMucMenu)

# KHU VỰC 2: QUẢN LÝ KHO HÀNG & MENU
class ChiTietNhapKhoInline(admin.TabularInline): model = ChiTietNhapKho; extra = 1; autocomplete_fields = ['nguyen_lieu']
@admin.register(PhieuNhapKho)
class PhieuNhapKhoAdmin(admin.ModelAdmin): list_display = ('id', 'nguoi_nhap', 'ngay_nhap'); inlines = [ChiTietNhapKhoInline]; list_filter = ('ngay_nhap', 'nguoi_nhap')
@admin.register(NguyenLieu)
class NguyenLieuAdmin(admin.ModelAdmin): list_display = ('ten_nguyen_lieu', 'so_luong_ton'); search_fields = ('ten_nguyen_lieu',)
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin): list_display = ('ten_mon', 'danh_muc', 'don_gia', 'is_available'); list_filter = ('danh_muc', 'is_available'); search_fields = ('ten_mon',)

# -----------------------------------------------------------------------------
# KHU VỰC 3: VẬN HÀNH QUÁN NET (ĐÃ THÊM ACTIONS)
# -----------------------------------------------------------------------------

@admin.register(May)
class MayAdmin(admin.ModelAdmin):
    list_display = ('ten_may', 'loai_may', 'trang_thai')
    list_filter = ('trang_thai', 'loai_may')
    search_fields = ('ten_may',)
    
    # --- ACTION MỚI ---
    actions = ['mo_may_tra_sau', 'mo_may_tra_truoc']

    @admin.action(description='Mở máy cho khách vãng lai (Trả sau)')
    def mo_may_tra_sau(self, request, queryset):
        for may in queryset.filter(trang_thai='TRONG'):
            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=request.user.nhanvien, # Giả định user là nhân viên
                hinh_thuc=PhienSuDung.HinhThuc.TRA_SAU
            )
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
        self.message_user(request, "Đã mở máy thành công.", messages.SUCCESS)

    @admin.action(description='Mở máy cho khách thành viên (Trả trước)')
    def mo_may_tra_truoc(self, request, queryset):
        # Logic này cần một form trung gian để chọn khách hàng, sẽ phức tạp hơn.
        # Tạm thời để placeholder.
        self.message_user(request, "Chức năng này cần giao diện POS để chọn khách hàng.", messages.WARNING)

    # Giữ lại code hiển thị đồng hồ
    def change_view(self, request, object_id, form_url='', extra_context=None):
        # ... (code giữ nguyên như trước)
        extra_context = extra_context or {}
        try:
            may_obj = self.get_object(request, object_id)
            if may_obj and may_obj.trang_thai == 'DANG_SU_DUNG':
                phien_hien_tai = PhienSuDung.objects.get(may_id=object_id, trang_thai='DANG_DIEN_RA')
                extra_context['phien_hien_tai'] = phien_hien_tai
        except PhienSuDung.DoesNotExist:
            extra_context['phien_hien_tai'] = None
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


@admin.register(PhienSuDung)
class PhienSuDungAdmin(admin.ModelAdmin):
    list_display = ('id', 'may', 'hinh_thuc', 'khach_hang', 'trang_thai', 'thoi_gian_bat_dau')
    list_filter = ('trang_thai', 'hinh_thuc')
    
    # --- ACTION MỚI ---
    actions = ['ket_thuc_va_lap_hoa_don']

    @admin.action(description='Kết thúc phiên & Lập hóa đơn')
    def ket_thuc_va_lap_hoa_don(self, request, queryset):
        for phien in queryset.filter(trang_thai='DANG_DIEN_RA'):
            # 1. Chốt thời gian và trạng thái
            phien.thoi_gian_ket_thuc = timezone.now()
            phien.trang_thai = 'DA_KET_THUC'
            
            # 2. Tính tiền giờ
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
            # 3. Tính tiền dịch vụ chưa thanh toán
            tien_dich_vu = phien.cac_don_hang.filter(
                trang_thai_thanh_toan='CHUA_THANH_TOAN'
            ).aggregate(total=Sum('tong_tien'))['total'] or 0
            
            # 4. Tạo hóa đơn
            hoa_don = HoaDon.objects.create(
                tong_tien_gio=tien_gio,
                tong_tien_dich_vu=tien_dich_vu,
                phai_thanh_toan=tien_gio + tien_dich_vu
            )
            phien.hoa_don = hoa_don
            phien.save()
            
            # 5. Cập nhật lại trạng thái máy
            phien.may.trang_thai = 'TRONG'
            phien.may.save()
        self.message_user(request, "Đã lập hóa đơn thành công.", messages.SUCCESS)

@admin.register(HoaDon)
class HoaDonAdmin(admin.ModelAdmin):
    list_display = ('id', 'phien_su_dung', 'trang_thai', 'phai_thanh_toan')
    list_filter = ('trang_thai',)
    readonly_fields = ('tong_tien_gio', 'tong_tien_dich_vu', 'phai_thanh_toan')

    # --- ACTION MỚI ---
    actions = ['thanh_toan_hoa_don']
    
    @admin.action(description='Xác nhận thanh toán hóa đơn (tiền mặt/ck)')
    def thanh_toan_hoa_don(self, request, queryset):
        for hoa_don in queryset.filter(trang_thai='CHUA_THANH_TOAN'):
            GiaoDichTaiChinh.objects.create(
                nhan_vien_thuc_hien=request.user.nhanvien,
                hoa_don_lien_quan=hoa_don,
                khach_hang=hoa_don.phien_su_dung.khach_hang,
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                so_tien=hoa_don.phai_thanh_toan
            )
            hoa_don.trang_thai = 'DA_THANH_TOAN'
            hoa_don.save()
        self.message_user(request, "Đã xác nhận thanh toán thành công.", messages.SUCCESS)


# ... Các lớp admin khác giữ nguyên, chỉ thêm action cho DonHangDichVu
class ChiTietDonHangInline(admin.TabularInline): model = ChiTietDonHang; extra = 1; autocomplete_fields = ['mon']; readonly_fields = ('don_gia_luc_dat', 'thanh_tien')
@admin.register(DonHangDichVu)
class DonHangDichVuAdmin(admin.ModelAdmin):
    list_display = ('id', 'phien_su_dung', 'trang_thai_thanh_toan', 'tong_tien')
    list_filter = ('trang_thai_thanh_toan',)
    inlines = [ChiTietDonHangInline]
    readonly_fields = ('phien_su_dung', 'tong_tien')
    
    # --- ACTION MỚI ---
    actions = ['thanh_toan_order_le']

    @admin.action(description='Thanh toán ngay order này (tiền mặt/ck)')
    def thanh_toan_order_le(self, request, queryset):
        for order in queryset.filter(trang_thai_thanh_toan='CHUA_THANH_TOAN'):
            GiaoDichTaiChinh.objects.create(
                nhan_vien_thuc_hien=request.user.nhanvien,
                order_le_lien_quan=order,
                khach_hang=order.phien_su_dung.khach_hang,
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                so_tien=order.tong_tien
            )
            order.trang_thai_thanh_toan = 'DA_THANH_TOAN_NGAY'
            order.save()
        self.message_user(request, "Đã thanh toán order lẻ thành công.", messages.SUCCESS)

# KHU VỰC 4: TÀI CHÍNH & BÁO CÁO
@admin.register(GiaoDichTaiChinh)
class GiaoDichTaiChinhAdmin(admin.ModelAdmin):
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