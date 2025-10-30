# quanlynet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # URL gốc / sẽ xử lý login, logout, home của accounts
    path('', include('accounts.urls')), 
    
    path('admin/', admin.site.urls),
    path('pos/', include('quanly.urls')), 
    path('dashboard/', include('dashboard.urls')),
    path('api/dashboard/', include('dashboard.api_urls')),
    
    # ✅ Thêm dòng này để bật toàn bộ POS API
    path('api/', include('quanly.api_urls')),  
    
    # GIỮ LẠI PATH ACCOUNTS ĐỂ XỬ LÝ /accounts/login, /accounts/logout, v.v.
    path('accounts/', include('accounts.urls')), 
]
