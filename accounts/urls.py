# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView
from django.conf import settings # <<< CẦN THÊM DÒNG NÀY

urlpatterns = [
    # Login tùy chỉnh
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # Logout (next_page sẽ lấy từ LOGOUT_REDIRECT_URL trong settings)
    path('logout/', auth_views.LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    
    # ... (Các URL khác)
]