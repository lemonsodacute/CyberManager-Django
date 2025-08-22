# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TaiKhoan

class TaiKhoanAdmin(UserAdmin):
    """
    Tùy chỉnh cách hiển thị model TaiKhoan trong trang Admin.
    """
    # Các cột sẽ hiển thị trong danh sách người dùng
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'loai_tai_khoan')
    
    # Thêm mục "Phân loại tài khoản" vào form khi bạn bấm vào để xem/sửa một người dùng
    fieldsets = UserAdmin.fieldsets + (
        ('Phân loại tài khoản', {'fields': ('loai_tai_khoan',)}),
    )
    # Thêm mục "Phân loại tài khoản" vào form khi bạn bấm "Add" để tạo người dùng mới
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Phân loại tài khoản', {'fields': ('loai_tai_khoan',)}),
    )

# Lệnh quyết định: Đăng ký model TaiKhoan với các tùy chỉnh hiển thị ở trên
admin.site.register(TaiKhoan, TaiKhoanAdmin)
