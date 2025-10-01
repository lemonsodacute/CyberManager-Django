# quanly/views.py (ĐÃ SỬA VÀ DỌN DẸP LỖI CÚ PHÁP & LOGIC)

from django.shortcuts import render, redirect # <<< CẦN CÓ
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model # <<< DÙNG ĐỂ TRUY CẬP CONSTANTS LOAI_TAI_KHOAN

# Lấy custom user model (TaiKhoan)
TaiKhoan = get_user_model()
from .models import NhanVien


# <<< DECORATOR CHUYÊN BIỆT ĐỂ CHẶN ADMIN KHỎI POS >>>
# Nếu là Admin, sẽ bị chuyển hướng đến Dashboard
def cashier_access_required(view_func):
    """
    Decorator: Đảm bảo người dùng là Nhân viên (KHÔNG phải Admin), 
    nếu là Admin thì chuyển hướng về Dashboard.
    """
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # 1. Nếu chưa đăng nhập, Django tự xử lý
        if not user.is_authenticated:
            # Sẽ được chuyển hướng đến LOGIN_URL của settings
            return view_func(request, *args, **kwargs) 
            
        # 2. CHẶN ADMIN: Nếu là staff VÀ loai_tai_khoan là ADMIN -> Chuyển về Dashboard
        if user.is_staff and user.loai_tai_khoan == TaiKhoan.LoaiTaiKhoan.ADMIN:
            return redirect(reverse_lazy('dashboard_home')) # <<< CHẶN VÀ CHUYỂN HƯỚNG

        # 3. Cho phép tiếp tục nếu là Nhân viên
        return view_func(request, *args, **kwargs)
        
    # Bọc wrapper bằng @login_required để đảm bảo user phải đăng nhập
    # Note: Hàm này phải được đặt ngay trên các view
    return login_required(wrapper) 


# -----------------------------------------------------------
# CÁC VIEW CỦA ỨNG DỤNG QUANLY (POS)
# -----------------------------------------------------------

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def pos_view(request):
    """View tổng quan máy (POS)."""
    return render(request, 'quanly/pos.html')

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def order_view(request):
    """View để hiển thị trang Order dịch vụ."""
    return render(request, 'quanly/order.html')

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def retail_order_view(request):
    """View để hiển thị trang POS Bán Lẻ chuyên dụng."""
    return render(request, 'quanly/retail_order.html')

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def inventory_view(request):
    """View để hiển thị trang Quản Lý Kho."""
    return render(request, 'quanly/inventory.html')

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def customer_management_view(request):
    """View để hiển thị trang Quản lý khách hàng."""
    return render(request, 'quanly/customer_management.html')

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def reports_view(request):
    """View để hiển thị trang Báo cáo và Lịch sử."""
    staffs = NhanVien.objects.select_related('tai_khoan').all()
    context = {
        'staff_list': staffs
    }
    return render(request, 'quanly/reports.html', context)