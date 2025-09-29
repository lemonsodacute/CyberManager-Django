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


@user_passes_test(is_staff_user, login_url='/pos/')
def machine_management_view(request):
    """View để hiển thị trang Quản lý Máy."""
    return render(request, 'dashboard/machine_management.html')

@user_passes_test(is_staff_user, login_url='/pos/')
def reports_view(request):
    """View để hiển thị trang Báo cáo."""
    return render(request, 'dashboard/reports.html')
@user_passes_test(is_staff_user, login_url='/pos/')
def customer_analytics_view(request):
    """View để hiển thị trang Phân tích Khách hàng."""
    return render(request, 'dashboard/customer_analytics.html')
# Thêm vào cuối file dashboard/views.py

@user_passes_test(is_staff_user, login_url='/pos/')
def customer_detail_view(request, pk):
    """View để hiển thị trang Chi tiết Khách hàng."""
    # Truyền customer_id vào context để JavaScript có thể lấy
    context = {'customer_id': pk}
    return render(request, 'dashboard/customer_detail.html', context)


@user_passes_test(is_staff_user, login_url='/pos/')
def promotion_management_view(request):
    """View để hiển thị trang Quản lý Khuyến mãi."""
    return render(request, 'dashboard/promotion_management.html')