# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home_view, name='dashboard_home'),
    # Trong tương lai, bạn có thể thêm các trang khác ở đây
    # path('users/', views.user_management_view, name='dashboard_users'),
    
    
    path('inventory/', views.inventory_management_view, name='dashboard_inventory'),
    
    path('users/', views.user_management_view, name='dashboard_users'),
    path('users/add/', views.add_user_view, name='dashboard_add_user'),
    
    path('menu/', views.menu_management_view, name='dashboard_menu'),
    
    path('machines/', views.machine_management_view, name='dashboard_machines'),
    
     path('reports/', views.reports_view, name='dashboard_reports'),
]