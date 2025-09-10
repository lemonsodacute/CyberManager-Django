# quanly/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied

# (Tùy chọn) Một hàm kiểm tra để đảm bảo chỉ nhân viên mới vào được trang POS
def is_nhan_vien(user):
    # Giả sử bạn có một cách để kiểm tra user có phải là NhanVien không
    # Ví dụ: user.groups.filter(name='NhanVien').exists() hoặc hasattr(user, 'nhanvien')
    # Ở đây tôi dùng hasattr cho đơn giản, bạn cần điều chỉnh cho phù hợp với model NhanVien của bạn
    return hasattr(user, 'nhanvien')

# Sử dụng decorator để bảo vệ view
# @user_passes_test(is_nhan_vien, login_url='/accounts/login/') # Bật dòng này nếu bạn muốn bảo vệ chặt chẽ hơn
@login_required(login_url='/accounts/login/') # Giữ decorator login_required là bắt buộc
def pos_view(request):
    """
    View này CHỈ có một nhiệm vụ duy nhất: render ra bộ khung HTML của trang POS.
    Toàn bộ dữ liệu và logic sẽ được xử lý bởi JavaScript và các API.
    """
    # <<< THAY ĐỔI TẠI ĐÂY >>>
    # Đường dẫn đúng phải là 'ten_app/ten_file.html'
    return render(request, 'quanly/pos.html')


@login_required(login_url='/accounts/login/') # Cũng nên bảo vệ trang order
def order_view(request):
    """View để hiển thị trang Order dịch vụ."""
    # <<< THAY ĐỔI TẠI ĐÂY >>>
    # Đường dẫn đúng phải là 'ten_app/ten_file.html'
    return render(request, 'quanly/order.html')


@login_required(login_url='/accounts/login/')
def retail_order_view(request):
    """View để hiển thị trang POS Bán Lẻ chuyên dụng."""
    return render(request, 'quanly/retail_order.html')

@login_required(login_url='/accounts/login/')
def inventory_view(request):
    """View để hiển thị trang Quản Lý Kho."""
    return render(request, 'quanly/inventory.html')