# # accounts/views.py

# from django.urls import reverse_lazy
# from django.contrib.auth.views import LoginView

# # ĐÂY LÀ CLASS MÀ FILE URLS.PY ĐANG TÌM KIẾM
# class CustomLoginView(LoginView):
#     """
#     Tùy chỉnh LoginView để chuyển hướng người dùng dựa trên vai trò của họ.
#     """
#     def get_success_url(self):
#         # Lấy thông tin người dùng vừa đăng nhập thành công
#         user = self.request.user
        
#         # Kiểm tra vai trò (loai_tai_khoan) và quyết định URL
#         if user.is_authenticated:
#             if user.loai_tai_khoan == 'ADMIN' or user.loai_tai_khoan == 'NHANVIEN':
#                 # Nếu là Admin hoặc Nhân viên, chuyển đến trang Dashboard
#                 return reverse_lazy('dashboard') 
#             elif user.loai_tai_khoan == 'KHACHHANG':
#                 # Nếu là Khách hàng, sau này sẽ chuyển đến trang profile
#                 return reverse_lazy('dashboard') # Tạm thời
        
#         # Nếu không rơi vào các trường hợp trên, dùng URL mặc định
#         return super().get_success_url()