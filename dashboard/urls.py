# dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Giao diện chính (Dashboard Home)
    path('', views.dashboard_home_view, name='dashboard_home'),
    
    # Giao diện Quản Lý
    path('menu/', views.menu_management_view, name='dashboard_menu'),
    path('promotions/', views.promotion_management_view, name='dashboard_promotions'), 
    path('machines/', views.machine_management_view, name='dashboard_machines'),
    path('inventory/', views.inventory_management_view, name='dashboard_inventory'),
    path('users/', views.user_management_view, name='dashboard_users'),
    path('users/add/', views.add_user_view, name='dashboard_add_user'),
    
    # Giao diện Báo Cáo
    path('reports/', views.reports_view, name='dashboard_reports'),
    
    # Giao diện Phân Tích Khách Hàng
    path('customers/', views.customer_analytics_view, name='dashboard_customers'),
    
    # <<< DÒNG MỚI CẦN THÊM >>>
    path('customers/<int:pk>/', views.customer_detail_view, name='dashboard_customer_detail'),
]

# File quanlynet/urls.py của bạn đã đúng và không cần sửa.