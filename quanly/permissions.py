# quanly/permissions.py
# quanly/permissions.py (FIXED)

from rest_framework.permissions import BasePermission
from accounts.models import TaiKhoan 
class IsNhanVien(BasePermission):
    """
    FIXED: Quyền cho phép Staff là NHANVIEN truy cập các API POS.
    Chặn vai trò ADMIN (Chủ tiệm) không được can thiệp vào nghiệp vụ POS.
    """
    message = "Bạn không có quyền nhân viên để truy cập POS API. Vai trò của bạn là Admin."

    def has_permission(self, request, view):
        # 1. PHẢI CÓ SESSION ĐĂNG NHẬP
        if not request.user.is_authenticated:
            return False
            
        # 2. PHẢI LÀ NHÂN VIÊN VÀ KHÔNG PHẢI ADMIN (Chỉ chấp nhận loai_tai_khoan='NHANVIEN')
        # Admin có is_staff=True nhưng loai_tai_khoan='ADMIN'
        return request.user.is_staff and request.user.loai_tai_khoan == TaiKhoan.LoaiTaiKhoan.NHAN_VIEN
# ... (IsAdminRole giữ nguyên) ...

class IsAdminRole(BasePermission):
    """
    Quyền Admin cấp cao: Chỉ ADMIN (loai_tai_khoan = 'ADMIN').
    """
    message = "Chỉ Quản lý cấp cao (Admin Role) mới có quyền thực hiện hành động này."

    def has_permission(self, request, view):
        # Kiểm tra vai trò: Phải là Staff và loai_tai_khoan = ADMIN
        return request.user.is_staff and request.user.loai_tai_khoan == TaiKhoan.LoaiTaiKhoan.ADMIN