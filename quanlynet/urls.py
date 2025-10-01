# quanlynet/urls.py (Project Root)

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Cần phải đặt một trang mặc định (/) để chuyển hướng đến login
    path('', include('accounts.urls')), # <<< SỬA: Bắt đầu từ trang accounts/urls/ (nơi login được định nghĩa)
    
    path('admin/', admin.site.urls),
    path('pos/', include('quanly.urls')), 
    path('dashboard/', include('dashboard.urls')),
    path('api/dashboard/', include('dashboard.api_urls')),
    
    # <<< DÒNG NÀY PHẢI ĐƯỢC GIỮ LẠI VÀ CHỈ ĐỊNH RÕ RÀNG >>>
     path('', include('accounts.urls')),
     path('accounts/', include('accounts.urls')), 
    # XÓA HOẶC COMMENT CÁC DÒNG LOGIN/LOGOUT CŨ TẠI ĐÂY NẾU CÓ
]