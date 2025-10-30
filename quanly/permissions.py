# quanly/permissions.py
# quanly/permissions.py (FIXED)

from rest_framework.permissions import BasePermission
from accounts.models import TaiKhoan 
class IsNhanVien(BasePermission):
    """
    FIXED: Quyền cho phép Staff là NHANVIEN truy cập các API POS.
    Chặn vai trò ADMIN (Chủ tiệm) không được can thiệp vào nghiệp vụ POS.
    Nhưng cho phép SUPERUSER truy cập tất cả.
    """
    message = "Bạn không có quyền nhân viên để truy cập POS API. Vai trò của bạn là Admin."

    def has_permission(self, request, view):
        # 1. Phải đăng nhập
        if not request.user.is_authenticated:
            return False

        # ✅ Cho phép superuser truy cập toàn bộ POS API
        if request.user.is_superuser:
            return True

        # 2. Phải là nhân viên và không phải admin
        return request.user.is_staff and request.user.loai_tai_khoan == TaiKhoan.LoaiTaiKhoan.NHAN_VIEN

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        # ✅ Nếu là superuser, cho phép truy cập mọi nơi
        if user.is_superuser:
            return True

        # Các kiểm tra khác
        if hasattr(user, 'nhanvien'):
            nv = user.nhanvien
            if getattr(nv, 'vai_tro', '').upper() in ['ADMIN', 'QUANLY']:
                return True

        return False
