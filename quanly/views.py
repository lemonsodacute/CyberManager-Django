# quanly/views.py (ĐÃ SỬA VÀ DỌN DẸP LỖI CÚ PHÁP & LOGIC)

from django.shortcuts import render, redirect # <<< CẦN CÓ
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model # <<< DÙNG ĐỂ TRUY CẬP CONSTANTS LOAI_TAI_KHOAN

from decimal import Decimal
from datetime import timedelta
import math

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate

from django.db.models import Sum
from django.utils import timezone

from .models import NhanVien, May, PhienSuDung, KhachHang, GiaoDichTaiChinh

# Lấy custom user model (TaiKhoan)
TaiKhoan = get_user_model()
from .models import (
    NhanVien,
    May,
    PhienSuDung,
    GiaoDichTaiChinh,
    KhachHang,
)


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

@cashier_access_required
def pos_view(request):
    """View tổng quan máy (POS)."""

    today = timezone.localdate()

    # 1. Thống kê máy
    total_machines = May.objects.count()

    active_sessions_qs = PhienSuDung.objects.filter(
        trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA
    )

    active_machines = active_sessions_qs.values("may").distinct().count()
    usage_rate = round((active_machines / total_machines) * 100, 1) if total_machines else 0

    # 2. Doanh thu hôm nay (từ các giao dịch thanh toán)
    revenue_qs = GiaoDichTaiChinh.objects.filter(
        thoi_gian_giao_dich__date=today,
        loai_giao_dich__in=[
            GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
            GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
            GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK,
        ],
    )
    today_revenue = revenue_qs.aggregate(total=Sum("so_tien"))["total"] or 0

    # 3. Khách đang online
    online_customers_count = active_sessions_qs.filter(
        khach_hang__isnull=False
    ).values("khach_hang").distinct().count()

    # 4. Doanh thu theo ngày trong tuần hiện tại
    labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    start_of_week = today - timedelta(days=today.weekday())  # Thứ 2

    daily_revenue = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        total = GiaoDichTaiChinh.objects.filter(
            thoi_gian_giao_dich__date=day,
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK,
            ],
        ).aggregate(total=Sum("so_tien"))["total"] or 0

        daily_revenue.append({"label": labels[i], "value": float(total)})

    max_value = max((d["value"] for d in daily_revenue), default=0)
    for d in daily_revenue:
        d["percent"] = int(d["value"] / max_value * 100) if max_value else 0

    # 5. Donut chart: trạng thái máy
    radius = 80
    circumference = 2 * 3.1416 * radius
    used_length = circumference * usage_rate / 100
    free_length = circumference - used_length
    donut_dasharray = f"{used_length:.0f} {free_length:.0f}"

    # 6. Khách hàng gần đây (không dùng điểm tích lũy)
    recent_sessions = (
        PhienSuDung.objects.filter(khach_hang__isnull=False)
        .select_related("khach_hang__tai_khoan")
        .order_by("-thoi_gian_bat_dau")[:50]
    )

    recent_customers = []
    seen_ids: set[int] = set()

    for session in recent_sessions:
        kh = session.khach_hang
        if not kh:
            continue

        # KhachHang dùng primary key = tai_khoan, nên dùng pk
        if kh.pk in seen_ids:
            continue
        seen_ids.add(kh.pk)

        is_online = active_sessions_qs.filter(khach_hang=kh).exists()

        recent_customers.append(
            {
                "name": kh.username,
                "last_time": session.thoi_gian_bat_dau,
                "is_online": is_online,
            }
        )

        # Lấy tối đa 5 khách gần nhất
        if len(recent_customers) >= 5:
            break

    context = {
        "total_machines": total_machines,
        "active_machines": active_machines,
        "free_machines": max(total_machines - active_machines, 0),
        "usage_rate": usage_rate,
        "today_revenue": today_revenue,
        "online_customers_count": online_customers_count,
        "daily_revenue": daily_revenue,
        "donut_dasharray": donut_dasharray,
        "recent_customers": recent_customers,
    }

    return render(request, "quanly/pos.html", context)


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

@cashier_access_required # <<< DÙNG DECORATOR MỚI
def machine_map_view(request):
    return render(request, "quanly/machine_map.html")

def _time_ago_label(dt):
    if not dt:
        return "Không xác định"
    now = timezone.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Vừa xong"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} phút trước"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} tiếng trước"
    days = int(hours // 24)
    return f"{days} ngày trước"
