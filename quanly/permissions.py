# quanly/permissions.py

from rest_framework.permissions import BasePermission

class IsNhanVien(BasePermission):
    """
    Quyền tùy chỉnh để chỉ cho phép truy cập nếu người dùng là một nhân viên.
    """
    message = "Chỉ tài khoản nhân viên mới có quyền thực hiện hành động này."

    def has_permission(self, request, view):
        # request.user là đối tượng TaiKhoan đã được xác thực.
        # 'nhanvien' là related_name từ model NhanVien.
        return hasattr(request.user, 'nhanvien')