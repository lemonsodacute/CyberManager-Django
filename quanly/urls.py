# quanly/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Để trống, vì phần 'nhanvien/' đã được định nghĩa ở file cha
    path('', views.pos_view, name='pos_view'),
]