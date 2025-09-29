# quanly/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

# -----------------------------------------------------------------------------
# KHU VỰC 1: CÁC MODEL NỀN TẢNG
# -----------------------------------------------------------------------------

class NhanVien(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='nhanvien')
    def __str__(self): return f"Nhân viên: {self.tai_khoan.username}"

class KhachHang(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, related_name='khachhang')
    so_du = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Số dư")
    @property
    def username(self):
        return self.tai_khoan.username
    def __str__(self): return f"Khách hàng: {self.tai_khoan.username}"

class LoaiMay(models.Model):
    ten_loai = models.CharField(max_length=50, unique=True)
    don_gia_gio = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return self.ten_loai

class May(models.Model):
    class TrangThai(models.TextChoices):
        TRONG = 'TRONG', 'Trống'
        DANG_SU_DUNG = 'DANG_SU_DUNG', 'Đang sử dụng'
        HONG = 'HONG', 'Hỏng'

    ten_may = models.CharField(max_length=50, unique=True)
    loai_may = models.ForeignKey(LoaiMay, on_delete=models.PROTECT)
    trang_thai = models.CharField(
        max_length=20,
        choices=TrangThai.choices,
        default=TrangThai.TRONG
    )
    def __str__(self): return self.ten_may

# -----------------------------------------------------------------------------
# KHU VỰC 2: QUẢN LÝ MENU, KHO VÀ ĐỊNH LƯỢNG
# -----------------------------------------------------------------------------

class DanhMucMenu(models.Model):
    ten_danh_muc = models.CharField(max_length=100, unique=True, verbose_name="Tên danh mục")
    def __str__(self): return self.ten_danh_muc

class NguyenLieu(models.Model):
    ten_nguyen_lieu = models.CharField(max_length=100, unique=True, verbose_name="Tên hàng hóa")
    don_vi_tinh = models.CharField(max_length=20, verbose_name="Đơn vị tính")
    so_luong_ton = models.FloatField(default=0, verbose_name="Số lượng tồn kho")
    gia_von = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Giá vốn / Đơn vị")
    def __str__(self): return self.ten_nguyen_lieu

class MenuItem(models.Model):
    ten_mon = models.CharField(max_length=100, unique=True, verbose_name="Tên món")
    danh_muc = models.ForeignKey(DanhMucMenu, on_delete=models.PROTECT, verbose_name="Danh mục")
    don_gia = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Đơn giá bán")
    nguyen_lieu_thanh_phan = models.ManyToManyField(
        NguyenLieu,
        through='DinhLuong',
        related_name='menu_items'
    )
    is_available = models.BooleanField(default=True, verbose_name="Có sẵn?")
    def __str__(self): return self.ten_mon

class DinhLuong(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='dinh_luong')
    nguyen_lieu = models.ForeignKey(NguyenLieu, on_delete=models.PROTECT)
    so_luong_can = models.FloatField(verbose_name="Số lượng cần")

    class Meta:
        unique_together = ('menu_item', 'nguyen_lieu')

class KhuyenMai(models.Model):
    ma_khuyen_mai = models.CharField(max_length=50, unique=True)
    mo_ta = models.TextField()
    LOAI_GIAM_GIA_CHOICES = [('PHAN_TRAM', 'Phần trăm'), ('SO_TIEN', 'Số tiền cố định')]
    loai_giam_gia = models.CharField(max_length=20, choices=LOAI_GIAM_GIA_CHOICES)
    gia_tri = models.FloatField()
    ngay_bat_dau = models.DateTimeField()
    ngay_ket_thuc = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.ma_khuyen_mai
# Chu kỳ lặp lại
    LOAI_CHU_KY_CHOICES = [
        ('MOT_LAN', 'Áp dụng một lần (theo ngày bắt đầu/kết thúc)'),
        ('HANG_NGAY', 'Lặp lại Hằng ngày'),
        ('HANG_TUAN', 'Lặp lại Hàng tuần'),
        ('HANG_THANG', 'Lặp lại Hàng tháng'),
    ]
    chu_ky_lap_lai = models.CharField(
        max_length=20, 
        choices=LOAI_CHU_KY_CHOICES, 
        default='MOT_LAN',
        verbose_name="Chu kỳ lặp lại"
    )
    
    # Áp dụng cho các ngày trong tuần (Thứ 2 = 1, Chủ nhật = 7). Lưu dưới dạng chuỗi '3,5,7' (Thứ 3, Thứ 5, CN)
    ngay_trong_tuan = models.CharField(
        max_length=15, 
        blank=True, 
        null=True, 
        verbose_name="Các ngày trong tuần"
    )

# -----------------------------------------------------------------------------
# KHU VỰC 3: CA LÀM VIỆC
# -----------------------------------------------------------------------------

class LoaiCa(models.Model):
    ten_ca = models.CharField(max_length=100, unique=True, verbose_name="Tên ca")
    gio_bat_dau = models.TimeField(verbose_name="Giờ bắt đầu dự kiến")
    gio_ket_thuc = models.TimeField(verbose_name="Giờ kết thúc dự kiến")

    class Meta:
        verbose_name_plural = "Các Loại Ca"
    def __str__(self): return f"{self.ten_ca} ({self.gio_bat_dau.strftime('%H:%M')} - {self.gio_ket_thuc.strftime('%H:%M')})"

class CaLamViec(models.Model):
    class TrangThai(models.TextChoices):
        DANG_DIEN_RA = 'DANG_DIEN_RA', 'Đang diễn ra'
        DA_KET_THUC = 'DA_KET_THUC', 'Đã kết thúc'

    loai_ca = models.ForeignKey(LoaiCa, on_delete=models.PROTECT, verbose_name="Loại ca", null=True, blank=True)
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='cac_ca_lam_viec')
    thoi_gian_bat_dau_thuc_te = models.DateTimeField()
    thoi_gian_ket_thuc_thuc_te = models.DateTimeField(null=True, blank=True)
    ngay_lam_viec = models.DateField(default=timezone.now)
    tien_mat_ban_dau = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    trang_thai = models.CharField(max_length=20, choices=TrangThai.choices, default=TrangThai.DANG_DIEN_RA)
    tien_mat_cuoi_ca = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tiền mặt cuối ca (NV nhập)")
    tong_doanh_thu_he_thong = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Tổng doanh thu (hệ thống)")
    chenh_lech = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Chênh lệch")

    class Meta:
        verbose_name_plural = "Các Ca Làm Việc Thực Tế"
    def __str__(self):
        ten_ca_hien_thi = self.loai_ca.ten_ca if self.loai_ca else "Ca Tự Do"
        return f"{ten_ca_hien_thi} ngày {self.ngay_lam_viec.strftime('%d/%m')} - NV: {self.nhan_vien.tai_khoan.username}"

# -----------------------------------------------------------------------------
# KHU VỰC 4: CÁC MODEL VẬN HÀNH
# -----------------------------------------------------------------------------

class PhienSuDung(models.Model):
    class HinhThuc(models.TextChoices):
        TRA_SAU = 'TRA_SAU', 'Trả sau'
        TRA_TRUOC = 'TRA_TRUOC', 'Trả trước'

    class TrangThai(models.TextChoices):
        DANG_DIEN_RA = 'DANG_DIEN_RA', 'Đang diễn ra'
        DA_KET_THUC = 'DA_KET_THUC', 'Đã kết thúc'
        DA_HUY = 'DA_HUY', 'Đã hủy'

    may = models.ForeignKey(May, on_delete=models.PROTECT, related_name='cac_phien_su_dung')
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_phien_su_dung')
    nhan_vien_mo_phien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='cac_phien_da_mo')
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True)
    hinh_thuc = models.CharField(max_length=10, choices=HinhThuc.choices)
    thoi_gian_bat_dau = models.DateTimeField(default=timezone.now)
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True)
    trang_thai = models.CharField(max_length=20, choices=TrangThai.choices, default=TrangThai.DANG_DIEN_RA)
    def __str__(self): return f"Phiên {self.may.ten_may} lúc {timezone.localtime(self.thoi_gian_bat_dau).strftime('%H:%M')}"

class DonHangDichVu(models.Model):
    class LoaiDonHang(models.TextChoices):
        GHI_NO = 'GHI_NO', 'Ghi nợ'
        BAN_LE = 'BAN_LE', 'Bán lẻ'

    phien_su_dung = models.ForeignKey(PhienSuDung, on_delete=models.CASCADE, related_name='cac_don_hang', null=True, blank=True)
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_don_hang')
    loai_don_hang = models.CharField(max_length=10, choices=LoaiDonHang.choices, default=LoaiDonHang.GHI_NO)
    da_thanh_toan = models.BooleanField(default=False)
    tong_tien = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return f"Order #{self.id}"

class ChiTietDonHang(models.Model):
    don_hang = models.ForeignKey(DonHangDichVu, on_delete=models.CASCADE, related_name='chi_tiet')
    mon = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    so_luong = models.PositiveIntegerField(default=1)
    thanh_tien = models.DecimalField(max_digits=12, decimal_places=2)

class HoaDon(models.Model):
    phien_su_dung = models.OneToOneField(PhienSuDung, on_delete=models.PROTECT, related_name='hoa_don', null=True, blank=True)
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_hoa_don')
    khuyen_mai = models.ForeignKey(KhuyenMai, on_delete=models.SET_NULL, null=True, blank=True)
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    tong_tien_gio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tong_tien_dich_vu = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tien_giam_gia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tong_cong = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    da_thanh_toan = models.BooleanField(default=False)
    def __str__(self): return f"Hóa đơn #{self.id}" if not self.phien_su_dung else f"Hóa đơn #{self.id} cho {self.phien_su_dung}"

# -----------------------------------------------------------------------------
# KHU VỰC 5: SỔ CÁI TÀI CHÍNH
# -----------------------------------------------------------------------------

class GiaoDichTaiChinh(models.Model):
    class LoaiGiaoDich(models.TextChoices):
        NAP_TIEN = 'NAP_TIEN', 'Nạp tiền vào tài khoản thành viên'
        THANH_TOAN_HOA_DON = 'THANH_TOAN_HOA_DON', 'Thanh toán hóa đơn (Tiền mặt/Chuyển khoản)'
        THANH_TOAN_ORDER_LE = 'THANH_TOAN_ORDER_LE', 'Thanh toán order lẻ (Tiền mặt/Chuyển khoản)'
        THANH_TOAN_TK = 'THANH_TOAN_TK', 'Thanh toán hóa đơn (Trừ vào tài khoản)'
        ADMIN_ADJUST = 'ADMIN_ADJUST', 'Admin điều chỉnh'

    ca_lam_viec = models.ForeignKey('CaLamViec', on_delete=models.PROTECT, related_name='cac_giao_dich', verbose_name="Ca làm việc")
    hoa_don = models.ForeignKey('HoaDon', on_delete=models.SET_NULL, null=True, blank=True, related_name='cac_giao_dich', verbose_name="Hóa đơn")
    don_hang_le = models.ForeignKey('DonHangDichVu', on_delete=models.SET_NULL, null=True, blank=True, related_name='giao_dich', verbose_name="Đơn hàng lẻ")
    khach_hang = models.ForeignKey('KhachHang', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Khách hàng")
    loai_giao_dich = models.CharField(max_length=30, choices=LoaiGiaoDich.choices, verbose_name="Loại giao dịch")
    so_tien = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Số tiền")
    thoi_gian_giao_dich = models.DateTimeField(default=timezone.now, verbose_name="Thời gian giao dịch")
    ghi_chu = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Giao dịch tài chính"
        verbose_name_plural = "Sổ Cái Giao Dịch Tài Chính"
        ordering = ['-thoi_gian_giao_dich']

    def __str__(self):
        return f"[{self.get_loai_giao_dich_display()}] {self.so_tien:,.0f} VNĐ"

# -----------------------------------------------------------------------------
# KHU VỰC 6: QUẢN LÝ KHO VÀ KIỂM KÊ
# -----------------------------------------------------------------------------

class PhieuKiemKe(models.Model):
    ca_lam_viec = models.OneToOneField(CaLamViec, on_delete=models.PROTECT, related_name='phieu_kiem_ke')
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='cac_phieu_kiem_ke')
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    ghi_chu = models.TextField(blank=True, null=True)
    da_xac_nhan = models.BooleanField(default=False, help_text="Đánh dấu khi nhân viên đã chốt số liệu cuối cùng.")

    class Meta:
        verbose_name_plural = "Các Phiếu Kiểm Kê"
    def __str__(self):
        return f"Phiếu kiểm kê cho {self.ca_lam_viec}"

class ChiTietKiemKe(models.Model):
    phieu_kiem_ke = models.ForeignKey(PhieuKiemKe, on_delete=models.CASCADE, related_name='chi_tiet')
    nguyen_lieu = models.ForeignKey(NguyenLieu, on_delete=models.PROTECT)
    ton_he_thong = models.FloatField(verbose_name="Tồn hệ thống", help_text="Số lượng hệ thống ghi nhận tại thời điểm kiểm kê.")
    ton_thuc_te = models.FloatField(verbose_name="Tồn thực tế", help_text="Số lượng nhân viên đếm được.")
    chenh_lech = models.FloatField(verbose_name="Chênh lệch", default=0)

    class Meta:
        unique_together = ('phieu_kiem_ke', 'nguyen_lieu')

    def __str__(self):
        return f"{self.nguyen_lieu.ten_nguyen_lieu} (Thực tế: {self.ton_thuc_te})"
# quanly/models.py

class LichSuThayDoiKho(models.Model):
    class LoaiThayDoi(models.TextChoices):
        NHAP_KHO = 'NHAP_KHO', 'Nhập kho từ nhà cung cấp'
        HUY_HANG = 'HUY_HANG', 'Báo hỏng / Hủy hàng'
        DIEU_CHINH = 'DIEU_CHINH', 'Admin điều chỉnh thủ công'

    # <<< SỬA DÒNG DƯỚI ĐÂY >>>
    # Thêm null=True, blank=True để cho phép trường này có thể trống
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.SET_NULL, related_name='cac_thay_doi_kho', null=True, blank=True)
    
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT)
    nguyen_lieu = models.ForeignKey(NguyenLieu, on_delete=models.PROTECT)
    so_luong_thay_doi = models.FloatField(help_text="Số dương cho Nhập kho, số âm cho Hủy hàng.")
    loai_thay_doi = models.CharField(max_length=20, choices=LoaiThayDoi.choices)
    thoi_gian = models.DateTimeField(auto_now_add=True)
    ly_do = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Lịch Sử Thay Đổi Kho"

    def __str__(self):
        return f"[{self.get_loai_thay_doi_display()}] {self.so_luong_thay_doi} {self.nguyen_lieu.don_vi_tinh} {self.nguyen_lieu.ten_nguyen_lieu}"
