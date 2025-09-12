# quanly/urls.py (PHIÊN BẢN CHÍNH XÁC)

from django.urls import path, include  # Nhớ thêm 'include'
from . import views

urlpatterns = [
    # URL cho các trang giao diện người dùng (HTML)
    path('', views.pos_view, name='pos-view'), 
    path('order/', views.order_view, name='order-view'),

    path('retail/', views.retail_order_view, name='retail-order-view'),
     path('inventory/', views.inventory_view, name='inventory-view'),
      path('customers/', views.customer_management_view, name='customer-management-view'),
    path('api/', include('quanly.api_urls')),
]