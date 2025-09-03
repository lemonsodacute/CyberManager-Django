# quanly/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone



# -----------------------------------------------------------------------------
# KHU VỰC 1: CÁC MODEL NỀN TẢNG
# -----------------------------------------------------------------------------

class NhanVien(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    def __str__(self): return f"Nhân viên: {self.tai_khoan.username}"

class KhachHang(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    so_du = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Số dư")
    def __str__(self): return f"Khách hàng: {self.tai_khoan.username}"

class LoaiMay(models.Model):
    ten_loai = models.CharField(max_length=50, unique=True, verbose_name="Tên loại máy")
    don_gia_gio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Đơn giá/giờ")
    def __str__(self): return self.ten_loai

class May(models.Model):
    TRANG_THAI_CHOICES = [('TRONG', 'Trống'), ('DANG_SU_DUNG', 'Đang sử dụng'), ('HONG', 'Hỏng')]
    ten_may = models.CharField(max_length=50, unique=True, verbose_name="Tên máy")
    loai_may = models.ForeignKey(LoaiMay, on_delete=models.PROTECT, verbose_name="Loại máy")
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='TRONG', verbose_name="Trạng thái")
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
    def __str__(self): return self.ten_nguyen_lieu

class MenuItem(models.Model):
    ten_mon = models.CharField(max_length=100, unique=True, verbose_name="Tên món")
    danh_muc = models.ForeignKey(DanhMucMenu, on_delete=models.PROTECT, verbose_name="Danh mục")
    don_gia = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Đơn giá bán")
    nguyen_lieu_thanh_phan = models.ManyToManyField(NguyenLieu, through='DinhLuong', related_name='mon_lien_quan')
    is_available = models.BooleanField(default=True, verbose_name="Có sẵn?")
    def __str__(self): return self.ten_mon

class DinhLuong(models.Model):
    mon = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    nguyen_lieu = models.ForeignKey(NguyenLieu, on_delete=models.CASCADE)
    so_luong_can = models.FloatField(verbose_name="Số lượng cần")

# -----------------------------------------------------------------------------
# KHU VỰC 3: CA LÀM VIỆC VÀ QUẢN LÝ KHO THEO CA
# -----------------------------------------------------------------------------

class LoaiCa(models.Model):
    """Định nghĩa các ca làm việc cố định do Admin thiết lập."""
    ten_ca = models.CharField(max_length=100, unique=True, verbose_name="Tên ca")
    gio_bat_dau = models.TimeField(verbose_name="Giờ bắt đầu dự kiến")
    gio_ket_thuc = models.TimeField(verbose_name="Giờ kết thúc dự kiến")
    
    class Meta:
        verbose_name = "Loại Ca"
        verbose_name_plural = "Các Loại Ca"
    def __str__(self): return f"{self.ten_ca} ({self.gio_bat_dau.strftime('%H:%M')} - {self.gio_ket_thuc.strftime('%H:%M')})"

class CaLamViec(models.Model):
    """Ghi lại một ca làm việc thực tế của nhân viên."""
    loai_ca = models.ForeignKey(LoaiCa, on_delete=models.PROTECT, verbose_name="Loại ca", null=True, blank=True)
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='cac_ca_lam_viec')
    thoi_gian_bat_dau_thuc_te = models.DateTimeField(verbose_name="Bắt đầu thực tế")
    thoi_gian_ket_thuc_thuc_te = models.DateTimeField(null=True, blank=True, verbose_name="Kết thúc thực tế")
    ngay_lam_viec = models.DateField(default=timezone.now, verbose_name="Ngày làm việc") 
    tien_mat_ban_dau = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tiền mặt đầu ca")
    tien_mat_cuoi_ca = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Tiền mặt cuối ca")
    tong_doanh_thu_he_thong = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Tổng doanh thu hệ thống")
    chenh_lech = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True, verbose_name="Chênh lệch")
    trang_thai = models.CharField(max_length=20, choices=[('DANG_DIEN_RA', 'Đang diễn ra'), ('DA_KET_THUC', 'Đã kết thúc')], default='DANG_DIEN_RA')
    # Các trường tổng kết sẽ được tính toán sau
    
    class Meta:
        verbose_name = "Ca Làm Việc Thực Tế"
        verbose_name_plural = "Các Ca Làm Việc Thực Tế"
        
    def __str__(self):
        # Hàm __str__ an toàn, xử lý trường hợp loai_ca là None
        local_time = timezone.localtime(self.thoi_gian_bat_dau_thuc_te)
        ten_ca_hien_thi = self.loai_ca.ten_ca if self.loai_ca else "Ca Tự Do"
        return f"{ten_ca_hien_thi} ngày {local_time.strftime('%d/%m')} - NV: {self.nhan_vien.tai_khoan.username}"

# ... Các model PhieuNhapKho, PhieuKiemKho có thể giữ lại hoặc đơn giản hóa nếu muốn...

# -----------------------------------------------------------------------------
# KHU VỰC 4: CÁC MODEL VẬN HÀNH
# -----------------------------------------------------------------------------

class PhienSuDung(models.Model):
    may = models.ForeignKey(May, on_delete=models.PROTECT, related_name='cac_phien_su_dung')
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_phien_su_dung')
    nhan_vien_mo_phien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, related_name='cac_phien_da_mo')
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True)
    hinh_thuc = models.CharField(max_length=10, choices=[('TRA_SAU', 'Trả sau'), ('TRA_TRUOC', 'Trả trước')])
    thoi_gian_bat_dau = models.DateTimeField(default=timezone.now)
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True)
    trang_thai = models.CharField(max_length=20, choices=[('DANG_DIEN_RA', 'Đang diễn ra'), ('DA_KET_THUC', 'Đã kết thúc'), ('DA_HUY', 'Đã hủy')], default='DANG_DIEN_RA')
    
    def __str__(self): 
        local_time = timezone.localtime(self.thoi_gian_bat_dau)
        return f"Phiên {self.may.ten_may} lúc {local_time.strftime('%H:%M')}"

class DonHangDichVu(models.Model):
    phien_su_dung = models.ForeignKey(PhienSuDung, on_delete=models.CASCADE, related_name='cac_don_hang', null=True, blank=True)
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_don_hang')
    da_thanh_toan = models.BooleanField(default=False, verbose_name="Đã thanh toán?")
    tong_tien = models.DecimalField(max_digits=12, decimal_places=2, default=0)

class ChiTietDonHang(models.Model):
    don_hang = models.ForeignKey(DonHangDichVu, on_delete=models.CASCADE, related_name='chi_tiet')
    mon = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    so_luong = models.PositiveIntegerField(default=1)
    thanh_tien = models.DecimalField(max_digits=12, decimal_places=2)

class KhuyenMai(models.Model):
    ma_khuyen_mai = models.CharField(max_length=50, unique=True)
    mo_ta = models.TextField()
    LOAI_GIAM_GIA_CHOICES = [('PHAN_TRAM', 'Phần trăm'), ('SO_TIEN', 'Số tiền cố định')]
    loai_giam_gia = models.CharField(max_length=20, choices=LOAI_GIAM_GIA_CHOICES)
    gia_tri = models.FloatField()
    ngay_bat_dau = models.DateTimeField()
    ngay_ket_thuc = models.DateTimeField()
    is_active = models.BooleanField(default=True)

class HoaDon(models.Model):
    phien_su_dung = models.OneToOneField(PhienSuDung, on_delete=models.PROTECT, related_name='hoa_don')
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_hoa_don')
    khuyen_mai = models.ForeignKey(KhuyenMai, on_delete=models.SET_NULL, null=True, blank=True)
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    tong_tien_gio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tong_tien_dich_vu = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tien_giam_gia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tong_cong = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    da_thanh_toan = models.BooleanField(default=False)
    
    def __str__(self): 
        # Hàm __str__ an toàn, xử lý trường hợp phien_su_dung có thể bị xóa
        if self.phien_su_dung:
            return f"Hóa đơn #{self.id} cho {self.phien_su_dung}"
        return f"Hóa đơn #{self.id} (phiên đã xóa)"

# -----------------------------------------------------------------------------
# KHU VỰC 5: SỔ CÁI TÀI CHÍNH
# -----------------------------------------------------------------------------

class GiaoDichTaiChinh(models.Model):
    LOAI_GIAO_DICH = [
        ('NAP_TIEN', 'Nạp tiền'),
        ('THANH_TOAN_HOA_DON', 'Thanh toán hóa đơn'),
        ('THANH_TOAN_ORDER_LE', 'Thanh toán order lẻ'),
        ('TRU_TIEN_GIO', 'Trừ tiền giờ tự động'),
        ('ADMIN_ADJUST', 'Admin điều chỉnh'),
    ]
    ca_lam_viec = models.ForeignKey(CaLamViec, on_delete=models.PROTECT, related_name='cac_giao_dich')
    hoa_don = models.ForeignKey(HoaDon, on_delete=models.SET_NULL, null=True, blank=True, related_name='cac_giao_dich')
    don_hang_le = models.ForeignKey(DonHangDichVu, on_delete=models.SET_NULL, null=True, blank=True, related_name='giao_dich')
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True)
    loai_giao_dich = models.CharField(max_length=30, choices=LOAI_GIAO_DICH)
    so_tien = models.DecimalField(max_digits=12, decimal_places=2)
    thoi_gian_giao_dich = models.DateTimeField(default=timezone.now)
<<<<<<< HEAD
    def __str__(self): return f"[{self.get_loai_giao_dich_display()}] {self.so_tien:,.0f} VNĐ"
    
# quanly/models.py

# ... (các imports và models hiện có của bạn) ...

# -----------------------------------------------------------------------------
# KHU VỰC MỚI: QUẢN LÝ CA LÀM VIỆC
# -----------------------------------------------------------------------------

class LoaiCa(models.Model):
    """Định nghĩa các loại ca làm việc với giờ giấc cụ thể."""
    ten_ca = models.CharField(max_length=100, unique=True, verbose_name="Tên loại ca")
    
    # --- THAY ĐỔI QUAN TRỌNG ---
    # Thay vì mô tả chung chung, ta định nghĩa giờ bắt đầu và kết thúc cụ thể
    gio_bat_dau = models.TimeField(verbose_name="Giờ bắt đầu theo quy định")
    gio_ket_thuc = models.TimeField(verbose_name="Giờ kết thúc theo quy định")
    
    # Giữ lại mô tả nhưng không bắt buộc, dùng để ghi chú thêm nếu cần
    mo_ta = models.TextField(blank=True, null=True, verbose_name="Mô tả (tùy chọn)")

    def __str__(self):
        # Hiển thị giờ giấc rõ ràng trong admin
        start_time = self.gio_bat_dau.strftime('%H:%M')
        end_time = self.gio_ket_thuc.strftime('%H:%M')
        return f"{self.ten_ca} ({start_time} - {end_time})"
    
    class Meta:
        verbose_name_plural = "Các Loại Ca"
        ordering = ['gio_bat_dau'] # Sắp xếp theo giờ bắt đầu ca
class CaLamViec(models.Model):
    """Ghi lại chi tiết một ca làm việc của nhân viên."""
    nhan_vien = models.ForeignKey(NhanVien, on_delete=models.PROTECT, verbose_name="Nhân viên")
    loai_ca = models.ForeignKey(LoaiCa, on_delete=models.PROTECT, verbose_name="Loại ca")
    
    thoi_gian_bat_dau_thuc_te = models.DateTimeField(default=timezone.now, verbose_name="Thời gian bắt đầu thực tế")
    thoi_gian_ket_thuc_thuc_te = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian kết thúc thực tế")
    
    tien_mat_ban_dau = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tiền mặt ban đầu trong két")
    tien_mat_cuoi_ca = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Tiền mặt cuối ca")

    ghi_chu = models.TextField(blank=True, null=True, verbose_name="Ghi chú")

    TRANG_THAI_CHOICES = [
        ('DANG_LAM', 'Đang làm việc'),
        ('DA_KET_THUC', 'Đã kết thúc'),
    ]
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='DANG_LAM', verbose_name="Trạng thái ca")

    def __str__(self):
        start_time = self.thoi_gian_bat_dau_thuc_te.strftime('%H:%M %d/%m')
        end_time = self.thoi_gian_ket_thuc_thuc_te.strftime('%H:%M %d/%m') if self.thoi_gian_ket_thuc_thuc_te else "Chưa kết thúc"
        return f"Ca {self.loai_ca.ten_ca} của {self.nhan_vien.tai_khoan.username} ({start_time} - {end_time})"

    class Meta:
        verbose_name_plural = "Các Ca Làm Việc"
        ordering = ['-thoi_gian_bat_dau_thuc_te'] # Sắp xếp theo thời gian bắt đầu giảm dần
        # Đảm bảo một nhân viên chỉ có một ca 'DANG_LAM' duy nhất
        constraints = [
            models.UniqueConstraint(fields=['nhan_vien'], condition=models.Q(trang_thai='DANG_LAM'), name='unique_active_shift_per_employee')
        ]
=======
    ghi_chu = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self): 
        return f"[{self.get_loai_giao_dich_display()}] {self.so_tien:,.0f} VNĐ"
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
