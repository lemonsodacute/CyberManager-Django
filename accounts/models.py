# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser

class TaiKhoan(AbstractUser):
    """
    Model người dùng tùy chỉnh, là nền tảng cho mọi tài khoản trong hệ thống.
    """
    
    # Định nghĩa các lựa chọn cố định cho vai trò (Loại tài khoản)
    class LoaiTaiKhoan(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        NHAN_VIEN = 'NHANVIEN', 'Nhân Viên'
        KHACH_HANG = 'KHACHHANG', 'Khách Hàng'

    # Thêm trường để phân loại vai trò người dùng
    loai_tai_khoan = models.CharField(
        max_length=10,
        choices=LoaiTaiKhoan.choices,
        default=LoaiTaiKhoan.KHACH_HANG, # Mặc định tài khoản mới là Khách Hàng
        verbose_name="Loại tài khoản" # Tên hiển thị trong trang admin
    )

    # Hàm này giúp hiển thị tên người dùng một cách thân thiện
    def __str__(self):
        return self.username