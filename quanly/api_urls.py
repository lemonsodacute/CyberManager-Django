# quanly/api_urls.py (PHIÊN BẢN CHÍNH XÁC CẦN KIỂM TRA)

from django.urls import path
from . import api_views

urlpatterns = [
    # APIs cho Máy và Phiên
    path('may/', api_views.DanhSachMayAPIView.as_view(), name='api_danh_sach_may'),
    path('may/<int:pk>/mo-may/', api_views.MoMayAPIView.as_view(), name='api_mo_may'),
    path('phien/<int:pk>/', api_views.ChiTietPhienAPIView.as_view(), name='api_chi_tiet_phien'),
    path('phien/<int:pk>/ket-thuc/', api_views.KetThucPhienAPIView.as_view(), name='api_ket_thuc_phien'),
    
    # --- DÒNG QUAN TRỌNG NHẤT NẰM Ở ĐÂY ---
    # Đảm bảo bạn có dòng này. Lỗi 404 là do thiếu nó.
    path('ca/hien-tai/', api_views.CaLamViecHienTaiAPIView.as_view(), name='api_ca_hien_tai'),
    
    # APIs khác cho Ca Làm Việc
    path('ca/bat-dau/', api_views.BatDauCaAPIView.as_view(), name='api_bat_dau_ca'),
    path('ca/ket-thuc/', api_views.KetThucCaAPIView.as_view(), name='api_ket_thuc_ca'),
    
    # APIs cho Menu & Order
    path('loai-ca/', api_views.DanhSachLoaiCaAPIView.as_view(), name='api_danh_sach_loai_ca'),
    path('menu/', api_views.MenuAPIView.as_view(), name='api_menu'),
    path('order/tao-moi/', api_views.TaoDonHangAPIView.as_view(), name='api_tao_order'),

 # <<< THÊM CÁC URL API CHO QUẢN LÝ KHO >>>
    path('kho/nguyen-lieu/', api_views.DanhSachNguyenLieuAPIView.as_view(), name='api_danh_sach_nguyen_lieu'),
    path('kho/nguyen-lieu/<int:pk>/bao-hong/', api_views.BaoHongNguyenLieuAPIView.as_view(), name='api_bao_hong'),
    path('kho/kiem-ke/', api_views.KiemKeCuoiCaAPIView.as_view(), name='api_kiem_ke_cuoi_ca'),
]