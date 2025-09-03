# quanly/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def pos_view(request):
    """
    View này CHỈ có một nhiệm vụ duy nhất: render ra bộ khung HTML của trang POS.
    Toàn bộ dữ liệu và logic sẽ được xử lý bởi JavaScript và các API.
    """
    # Không cần context, không cần truy vấn database ở đây.
    return render(request, 'nhanvien/pos.html')