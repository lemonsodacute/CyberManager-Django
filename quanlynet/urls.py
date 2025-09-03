# quanlynet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('quanly.api_urls')),
    path('nhanvien/', include('quanly.urls')),
    
    # THAY DÒNG CŨ BẰNG DÒNG NÀY
    path('accounts/', include('accounts.urls')),
]