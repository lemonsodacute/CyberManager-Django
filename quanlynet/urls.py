# quanlynet/urls.py

from django.contrib import admin
from django.urls import path, include 
# quanlynet/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('quanly.api_urls')), 
    
    # Sửa lại thành 'nhanvien/'
    path('nhanvien/', include('quanly.urls')),
    
    path('accounts/', include('django.contrib.auth.urls')),
]