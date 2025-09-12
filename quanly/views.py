# quanly/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# <<< THÊM DÒNG IMPORT BỊ THIẾU VÀO ĐÂY >>>
from .models import NhanVien

@login_required(login_url='/accounts/login/')
def pos_view(request):
    """
    View này CHỈ có một nhiệm vụ duy nhất: render ra bộ khung HTML của trang POS.
    Toàn bộ dữ liệu và logic sẽ được xử lý bởi JavaScript và các API.
    """
    return render(request, 'quanly/pos.html')


@login_required(login_url='/accounts/login/')
def order_view(request):
    """View để hiển thị trang Order dịch vụ."""
    return render(request, 'quanly/order.html')


@login_required(login_url='/accounts/login/')
def retail_order_view(request):
    """View để hiển thị trang POS Bán Lẻ chuyên dụng."""
    return render(request, 'quanly/retail_order.html')


@login_required(login_url='/accounts/login/')
def inventory_view(request):
    """View để hiển thị trang Quản Lý Kho."""
    return render(request, 'quanly/inventory.html')


@login_required(login_url='/accounts/login/')
def customer_management_view(request):
    """View để hiển thị trang Quản lý khách hàng."""
    return render(request, 'quanly/customer_management.html')


@login_required(login_url='/accounts/login/')
def reports_view(request):
    """View để hiển thị trang Báo cáo và Lịch sử."""
    # Dòng này trước đây gây lỗi vì thiếu import NhanVien
    staffs = NhanVien.objects.select_related('tai_khoan').all()
    context = {
        'staff_list': staffs
    }
    return render(request, 'quanly/reports.html', context)