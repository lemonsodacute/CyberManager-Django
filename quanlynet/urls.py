# quanlynet/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pos/', include('quanly.urls')), 
    
    path(
        'accounts/login/', 
        auth_views.LoginView.as_view(template_name='accounts/login.html'), 
        name='login'
    ),
    # DÒNG QUAN TRỌNG NẰM Ở ĐÂY
     path(
        'accounts/logout/', 
        auth_views.LogoutView.as_view(next_page='/accounts/login/'), 
        name='logout'
    ),
      path('api/dashboard/', include('dashboard.api_urls')),
        path('dashboard/', include('dashboard.urls')),
        
       
]
LOGOUT_ON_GET = True