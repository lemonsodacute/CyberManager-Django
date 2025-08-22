from django.urls import path
from . import api_views

urlpatterns = [
    path('may/', api_views.DanhSachMayAPIView.as_view(), name='api_danh_sach_may'),
    path('may/<int:pk>/mo-may/', api_views.MoMayAPIView.as_view(), name='api_mo_may'),
    
    # --- DÁN CÁC DÒNG MỚI VÀO ĐÂY ---
    path('phien/<int:pk>/', api_views.ChiTietPhienAPIView.as_view(), name='api_chi_tiet_phien'),
    path('phien/<int:pk>/ket-thuc/', api_views.KetThucPhienAPIView.as_view(), name='api_ket_thuc_phien'),
]