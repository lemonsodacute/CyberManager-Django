# quanly/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone



# -----------------------------------------------------------------------------
# KHU VỰC 1: CÁC MODEL NỀN TẢNG (Người dùng, Máy) - Ít thay đổi
# -----------------------------------------------------------------------------

class NhanVien(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, limit_choices_to={'loai_tai_khoan': 'NHANVIEN'})
    chuc_vu = models.CharField(max_length=100, default="Nhân viên", verbose_name="Chức vụ")
    def __str__(self): return f"Nhân viên: {self.tai_khoan.username}"

class KhachHang(models.Model):
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True, limit_choices_to={'loai_tai_khoan': 'KHACHHANG'})
    so_du = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Số dư tài khoản")
    def __str__(self): return f"Khách hàng: {self.tai_khoan.username}"

class LoaiMay(models.Model):
    ten_loai = models.CharField(max_length=50, unique=True, verbose_name="Tên loại máy")
    don_gia_gio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Đơn giá mỗi giờ (VNĐ/giờ)")
    def __str__(self): return self.ten_loai

class May(models.Model):
    ten_may = models.CharField(max_length=50, unique=True, verbose_name="Tên máy")
    loai_may = models.ForeignKey(LoaiMay, on_delete=models.PROTECT, verbose_name="Loại máy")
    TRANG_THAI_CHOICES = [('TRONG', 'Trống'), ('DANG_SU_DUNG', 'Đang sử dụng'), ('HONG', 'Hỏng')]
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='TRONG', verbose_name="Trạng thái")
    def __str__(self): return self.ten_may

# -----------------------------------------------------------------------------
# KHU VỰC 2: QUẢN LÝ MENU VÀ KHO HÀNG (Đã tái cấu trúc)
# -----------------------------------------------------------------------------

class DanhMucMenu(models.Model):
    """MỚI: Để phân loại món ăn (Đồ ăn, Nước uống, Combo)"""
    ten_danh_muc = models.CharField(max_length=100, unique=True, verbose_name="Tên danh mục")
    def __str__(self): return self.ten_danh_muc

class NguyenLieu(models.Model):
    """Lưu trữ các nguyên vật liệu hoặc hàng hóa bán ra."""
    ten_nguyen_lieu = models.CharField(max_length=100, unique=True, verbose_name="Tên nguyên liệu/hàng hóa")
    don_vi_tinh = models.CharField(max_length=20, verbose_name="Đơn vị tính (VD: lon, gói, kg)")
    so_luong_ton = models.FloatField(default=0, verbose_name="Số lượng tồn kho (hệ thống tính)")
    def __str__(self): return self.ten_nguyen_lieu

class MenuItem(models.Model): # Đổi tên từ Menu để rõ nghĩa hơn
    """Một món trong menu, có thể liên kết với kho hoặc không."""
    ten_mon = models.CharField(max_length=100, unique=True, verbose_name="Tên món")
    danh_muc = models.ForeignKey(DanhMucMenu, on_delete=models.PROTECT, verbose_name="Danh mục")
    don_gia = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Đơn giá bán")
    # Liên kết 1-1 với kho, ví dụ "Nước Sting" trong menu sẽ link với "Lon Sting" trong kho
    nguyen_lieu_tuong_ung = models.ForeignKey(NguyenLieu, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hàng hóa trong kho (nếu có)")
    is_available = models.BooleanField(default=True, verbose_name="Còn hàng?")
    def __str__(self): return self.ten_mon

class PhieuNhapKho(models.Model):
    """MỚI: Ghi lại mỗi lần admin/nhân viên nhập hàng vào kho."""
    nguoi_nhap = models.ForeignKey(NhanVien, on_delete=models.PROTECT, verbose_name="Người nhập kho")
    ngay_nhap = models.DateTimeField(default=timezone.now, verbose_name="Ngày nhập")
    ghi_chu = models.TextField(blank=True, null=True)
    def __str__(self): return f"Phiếu nhập #{self.id} ngày {self.ngay_nhap.strftime('%d/%m/%Y')}"

class ChiTietNhapKho(models.Model):
    """MỚI: Chi tiết từng mặt hàng trong một phiếu nhập kho."""
    phieu_nhap = models.ForeignKey(PhieuNhapKho, on_delete=models.CASCADE, related_name="chi_tiet")
    nguyen_lieu = models.ForeignKey(NguyenLieu, on_delete=models.PROTECT, verbose_name="Nguyên liệu")
    so_luong = models.FloatField(verbose_name="Số lượng nhập")
    # Thêm đơn giá nhập để tính toán chi phí sau này
    don_gia_nhap = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Đơn giá nhập")

# -----------------------------------------------------------------------------
# KHU VỰC 3: CÁC MODEL CỐT LÕI VỀ VẬN HÀNH (Cấu trúc mới hoàn toàn)
# -----------------------------------------------------------------------------

class PhienSuDung(models.Model):
    """Ghi lại MỘT phiên sử dụng máy của khách."""
    class HinhThuc(models.TextChoices):
        TRA_SAU = 'TRA_SAU', 'Trả sau (khách vãng lai)'
        TRA_TRUOC = 'TRA_TRUOC', 'Trả trước (tài khoản thành viên)'
    
    may = models.ForeignKey(May, on_delete=models.PROTECT)
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True)
    nhan_vien_mo_phien = models.ForeignKey(NhanVien, on_delete=models.PROTECT)
    hinh_thuc = models.CharField(max_length=10, choices=HinhThuc.choices, default=HinhThuc.TRA_SAU)
    thoi_gian_bat_dau = models.DateTimeField(default=timezone.now)
    thoi_gian_ket_thuc = models.DateTimeField(null=True, blank=True)
    trang_thai = models.CharField(max_length=20, choices=[('DANG_DIEN_RA', 'Đang diễn ra'), ('DA_KET_THUC', 'Đã kết thúc')], default='DANG_DIEN_RA')
    # Mỗi phiên sẽ có duy nhất MỘT hóa đơn khi kết thúc
    hoa_don = models.OneToOneField('HoaDon', on_delete=models.SET_NULL, null=True, blank=True, related_name='phien_su_dung')
    def __str__(self): return f"Phiên {self.may.ten_may} ({self.thoi_gian_bat_dau.strftime('%d/%m %H:%M')})"

class DonHangDichVu(models.Model):
    """Lưu trữ MỘT lần order, có trạng thái thanh toán riêng."""
    phien_su_dung = models.ForeignKey(PhienSuDung, on_delete=models.CASCADE, related_name='cac_don_hang')
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    TRANG_THAI_THANH_TOAN_CHOICES = [
        ('CHUA_THANH_TOAN', 'Chưa thanh toán (cộng vào hóa đơn cuối)'),
        ('DA_THANH_TOAN_NGAY', 'Đã thanh toán ngay')
    ]
    trang_thai_thanh_toan = models.CharField(max_length=20, choices=TRANG_THAI_THANH_TOAN_CHOICES, default='CHUA_THANH_TOAN')
    tong_tien = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return f"Order #{self.id} cho phiên {self.phien_su_dung.id}"

class ChiTietDonHang(models.Model):
    don_hang = models.ForeignKey(DonHangDichVu, on_delete=models.CASCADE, related_name='chi_tiet')
    mon = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    so_luong = models.PositiveIntegerField(default=1)
    don_gia_luc_dat = models.DecimalField(max_digits=10, decimal_places=2)
    thanh_tien = models.DecimalField(max_digits=12, decimal_places=2)

class HoaDon(models.Model):
    """Hóa đơn TỔNG HỢP được tạo ra khi một PhienSuDung kết thúc."""
    TRANG_THAI_CHOICES = [('CHUA_THANH_TOAN', 'Chưa thanh toán'), ('DA_THANH_TOAN', 'Đã thanh toán')]
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHUA_THANH_TOAN')
    tong_tien_gio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tong_tien_dich_vu = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Tiền dịch vụ (chưa trả)")
    phai_thanh_toan = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Hóa đơn #{self.id} - {self.phai_thanh_toan:,.0f} VNĐ"

# -----------------------------------------------------------------------------
# KHU VỰC 4: SỔ CÁI TÀI CHÍNH - NGUỒN DỮ LIỆU DUY NHẤT CHO BÁO CÁO
# -----------------------------------------------------------------------------

class GiaoDichTaiChinh(models.Model):
    """Ghi lại MỌI hoạt động tiền ra tiền vào."""
    class LoaiGiaoDich(models.TextChoices):
        NAP_TIEN = 'NAP_TIEN', 'Nạp tiền vào tài khoản'
        THANH_TOAN_HOA_DON = 'PAY_INVOICE', 'Thanh toán hóa đơn (tiền mặt/ck)'
        THANH_TOAN_ORDER_LE = 'PAY_ORDER', 'Thanh toán order lẻ (tiền mặt/ck)'
        TRU_TIEN_TAI_KHOAN = 'USE_BALANCE', 'Sử dụng tài khoản (trừ tiền giờ)'
    
    nhan_vien_thuc_hien = models.ForeignKey(NhanVien, on_delete=models.PROTECT)
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.SET_NULL, null=True, blank=True)
    # Có thể liên quan đến một hóa đơn tổng, hoặc một order lẻ
    hoa_don_lien_quan = models.ForeignKey(HoaDon, on_delete=models.SET_NULL, null=True, blank=True)
    order_le_lien_quan = models.ForeignKey(DonHangDichVu, on_delete=models.SET_NULL, null=True, blank=True)

    loai_giao_dich = models.CharField(max_length=20, choices=LoaiGiaoDich.choices)
    so_tien = models.DecimalField(max_digits=12, decimal_places=2)
    thoi_gian_giao_dich = models.DateTimeField(default=timezone.now)
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