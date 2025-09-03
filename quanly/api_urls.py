# quanly/api_urls.py

from django.urls import path
from . import api_views

urlpatterns = [
    # API của máy
    path('may/', api_views.DanhSachMayAPIView.as_view(), name='api_danh_sach_may'),
    path('may/<int:pk>/mo-may/', api_views.MoMayAPIView.as_view(), name='api_mo_may'),
    
    # API của phiên sử dụng
    path('phien/<int:pk>/', api_views.ChiTietPhienAPIView.as_view(), name='api_chi_tiet_phien'),
    path('phien/<int:pk>/ket-thuc/', api_views.KetThucPhienAPIView.as_view(), name='api_ket_thuc_phien'),

    # API của ca làm việc
    path('loai-ca/', api_views.LoaiCaListAPIView.as_view(), name='api_loai_ca_list'),
    path('ca/hien-tai/', api_views.CaHienTaiAPIView.as_view(), name='api_ca_hien_tai'), # <-- ĐÃ SỬA
    path('ca/bat-dau/', api_views.BatDauCaAPIView.as_view(), name='api_bat_dau_ca'),
    path('ca/ket-thuc/', api_views.KetThucCaAPIView.as_view(), name='api_ket_thuc_ca'),
]