# accounts/views.py

from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html' 

    def get_success_url(self):
        user = self.request.user
        
        if user.is_authenticated:
            
           # 1. Nếu user là Admin Cấp cao
            if user.loai_tai_khoan == 'ADMIN':
                return reverse_lazy('dashboard_home') # <<< ĐI ĐẾN DASHBOARD
                
            # 2. Nếu user là Staff/Nhân viên (KHÔNG phải ADMIN)
            elif user.is_staff and user.loai_tai_khoan == 'NHANVIEN':
                return reverse_lazy('pos-view') # <<< ĐI ĐẾN POS
            
            # Nếu là Khách hàng
            elif user.loai_tai_khoan == 'KHACHHANG':
                 # Chuyển hướng mặc định đến trang dành cho Khách hàng
                 return reverse_lazy('home') 
            
        return super().get_success_url()