# quanly/views.py
# File này sẽ chứa các view cho giao diện người dùng sau này.
# quanly/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
@login_required
# @login_required # Sẽ bật lên sau để yêu cầu nhân viên phải đăng nhập
def pos_view(request):
    """
    View này chỉ đơn giản là render trang giao diện POS.
    Toàn bộ logic sẽ được xử lý bằng JavaScript ở phía client.
    """
    return render(request, 'nhanvien/pos.html')