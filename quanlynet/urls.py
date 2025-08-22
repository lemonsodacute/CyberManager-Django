# quanlynet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('quanly.api_urls')),
    path('nhanvien/', include('quanly.urls')),
    
    # --- DÒNG MỚI ---
    # Thêm URL cho việc đăng nhập/đăng xuất của Django
    path('accounts/', include('django.contrib.auth.urls')),
]
