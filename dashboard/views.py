# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

# Hàm kiểm tra xem user có phải là staff/admin không
def is_staff_user(user):
    return user.is_staff

# Decorator @user_passes_test sẽ kiểm tra quyền trước khi cho vào view
@user_passes_test(is_staff_user, login_url='/pos/') # Nếu không phải staff, chuyển về trang POS
def dashboard_home_view(request):
    """View để hiển thị trang chủ của Admin Dashboard."""
    return render(request, 'dashboard/home.html')



@user_passes_test(is_staff_user, login_url='/pos/')
def inventory_management_view(request):
    return render(request, 'dashboard/inventory.html')


@user_passes_test(is_staff_user, login_url='/pos/')
def user_management_view(request):
    return render(request, 'dashboard/user_management.html')

@user_passes_test(is_staff_user, login_url='/pos/')
def add_user_view(request):
    """View để hiển thị trang thêm người dùng cho Admin."""
    return render(request, 'dashboard/add_user.html')

@user_passes_test(is_staff_user, login_url='/pos/')
def menu_management_view(request):
    """View để hiển thị trang Quản lý Menu."""
    return render(request, 'dashboard/menu_management.html')