# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView # Import view tùy chỉnh của bạn

urlpatterns = [
    # Sử dụng CustomLoginView của bạn cho URL login
    path('login/', CustomLoginView.as_view(template_name='accounts/login.html'), name='login'),
    
    # Sử dụng LogoutView mặc định của Django, nhưng chỉ định trang sẽ đến sau khi logout
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]