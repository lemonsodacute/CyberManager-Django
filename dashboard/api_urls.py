# dashboard/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('summary/', api_views.DashboardSummaryAPIView.as_view(), name='dashboard_summary'),
     # <<< THÊM URL MỚI CHO QUẢN LÝ KHO >>>
    path('kiem-ke/', api_views.PhieuKiemKeListAPIView.as_view(), name='dashboard_kiemke_list'),
    path('kiem-ke/<int:pk>/xac-nhan/', api_views.XacNhanPhieuKiemKeAPIView.as_view(), name='dashboard_kiemke_xacnhan'),
    
    path('users/', api_views.UserListAPIView.as_view(), name='dashboard_user_list'),
    path('users/<int:pk>/action/', api_views.UserActionAPIView.as_view(), name='dashboard_user_action'),
# <<< THÊM CÁC URL MỚI CHO QUẢN LÝ MENU >>>
    path('menu/categories/', api_views.DanhMucMenuListAPIView.as_view(), name='dashboard_menucategory_list'),
    path('menu/items/', api_views.MenuItemListCreateAPIView.as_view(), name='dashboard_menuitem_list'),
    path('menu/items/<int:pk>/', api_views.MenuItemDetailAPIView.as_view(), name='dashboard_menuitem_detail'),
    
    path('menu/categories/<int:pk>/', api_views.DanhMucMenuDetailAPIView.as_view(), name='dashboard_menucategory_detail'),

    path('menu/items/', api_views.MenuItemListCreateAPIView.as_view(), name='dashboard_menuitem_list'),
    path('menu/items/<int:pk>/', api_views.MenuItemDetailAPIView.as_view(), name='dashboard_menuitem_detail'),
     # <<< THÊM CÁC URL MỚI CHO QUẢN LÝ TỒN KHO >>>
    path('inventory/items/', api_views.NguyenLieuListCreateAPIView.as_view(), name='dashboard_inventory_list'),
    path('inventory/items/<int:pk>/', api_views.NguyenLieuDetailAPIView.as_view(), name='dashboard_inventory_detail'),
    path('inventory/import/', api_views.NhapKhoAPIView.as_view(), name='dashboard_inventory_import'),
    
    # <<< THÊM CÁC URL MỚI CHO QUẢN LÝ MÁY >>>
    path('machines/types/', api_views.LoaiMayListCreateAPIView.as_view(), name='dashboard_machinetype_list'),
    path('machines/types/<int:pk>/', api_views.LoaiMayDetailAPIView.as_view(), name='dashboard_machinetype_detail'),
    path('machines/', api_views.MayListCreateAPIView.as_view(), name='dashboard_machine_list'),
    path('machines/<int:pk>/', api_views.MayDetailAPIView.as_view(), name='dashboard_machine_detail'),
    
    # <<< THÊM CÁC URL MỚI CHO BÁO CÁO >>>
    path('reports/summary/', api_views.ReportSummaryAPIView.as_view(), name='dashboard_report_summary'),
    path('reports/shifts/', api_views.CaLamViecListAPIView.as_view(), name='dashboard_shift_list'),
    path('reports/shifts/<int:pk>/', api_views.CaLamViecDetailAPIView.as_view(), name='dashboard_shift_detail'),
    # <<< THÊM URL MỚI CHO BÁO CÁO SẢN PHẨM >>>
    path('reports/product-performance/', api_views.ProductPerformanceAPIView.as_view(), name='dashboard_report_product'),
    
      # <<< THÊM URL MỚI CHO BÁO CÁO GIỜ CAO ĐIỂM >>>
    path('reports/peak-hours/', api_views.PeakHoursAPIView.as_view(), name='dashboard_report_peakhours'),
]