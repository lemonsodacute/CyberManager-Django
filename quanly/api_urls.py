# quanly/api_urls.py (PHIÊN BẢN CHÍNH XÁC CẦN KIỂM TRA)

from django.urls import path
from . import api_views
from django.db import models 

urlpatterns = [
  path('order/debt-list/', api_views.NhanVienNoDichVuListAPIView.as_view(), name='api_order_debt_list'),
    # ...
    path('order/<int:pk>/pay-debt/', api_views.ThanhToanNoDichVuAPIView.as_view(), name='api_order_pay_debt'),
      # APIs cho Khuyến mãi
    path('promotions/check/', api_views.CheckPromotionAPIView.as_view(), name='api_check_promotion'), # Cho đơn hàng dịch vụ
    # <<< THÊM URL MỚI CHO KIỂM TRA KHUYẾN MÃI NẠP TIỀN >>>
    path('promotions/check-topup/<int:pk>/', api_views.CheckTopupPromotionAPIView.as_view(), name='api_check_topup_promotion'), # Cho nạp tiền khách hàng (pk là khach_hang_id)
   # <<< THÊM URL MỚI ĐỂ LẤY DANH SÁCH MÃ KM NẠP TIỀN HỢP LỆ >>>
    path('promotions/active-topup-list/', api_views.GetActiveTopupPromotionsAPIView.as_view(), name='api_active_topup_promotions'),
    # <<< KẾT THÚC THÊM URL MỚI >>>
    # APIs cho Máy và Phiên
    path('may/', api_views.DanhSachMayAPIView.as_view(), name='api_danh_sach_may'),
    path('may/<int:pk>/mo-may/', api_views.MoMayAPIView.as_view(), name='api_mo_may'),
    path('phien/<int:pk>/', api_views.ChiTietPhienAPIView.as_view(), name='api_chi_tiet_phien'),
    path('phien/<int:pk>/ket-thuc/', api_views.KetThucPhienAPIView.as_view(), name='api_ket_thuc_phien'),
    
    # --- DÒNG QUAN TRỌNG NHẤT NẰM Ở ĐÂY ---
    # Đảm bảo bạn có dòng này. Lỗi 404 là do thiếu nó.
    path('ca/hien-tai/', api_views.CaLamViecHienTaiAPIView.as_view(), name='api_ca_hien_tai'),
    
    # APIs khác cho Ca Làm Việc
    path('ca/bat-dau/', api_views.BatDauCaAPIView.as_view(), name='api_bat_dau_ca'),
    path('ca/ket-thuc/', api_views.KetThucCaAPIView.as_view(), name='api_ket_thuc_ca'),
    
    # APIs cho Menu & Order
    path('loai-ca/', api_views.DanhSachLoaiCaAPIView.as_view(), name='api_danh_sach_loai_ca'),
    path('menu/', api_views.MenuAPIView.as_view(), name='api_menu'),
    path('order/tao-moi/', api_views.TaoDonHangAPIView.as_view(), name='api_tao_order'),

 # <<< THÊM CÁC URL API CHO QUẢN LÝ KHO >>>
    path('kho/nguyen-lieu/', api_views.DanhSachNguyenLieuAPIView.as_view(), name='api_danh_sach_nguyen_lieu'),
    path('kho/nguyen-lieu/<int:pk>/bao-hong/', api_views.BaoHongNguyenLieuAPIView.as_view(), name='api_bao_hong'),
    path('kho/kiem-ke/', api_views.KiemKeCuoiCaAPIView.as_view(), name='api_kiem_ke_cuoi_ca'),
    
      # <<< THÊM URL API CHO QUẢN LÝ KHÁCH HÀNG >>>
    path('khach-hang/', api_views.KhachHangListCreateAPIView.as_view(), name='api_khachhang_list_create'),
    path('khach-hang/<int:pk>/', api_views.KhachHangDetailAPIView.as_view(), name='api_khachhang_detail'),
    path('khach-hang/<int:pk>/nap-tien/', api_views.NapTienAPIView.as_view(), name='api_khachhang_nap_tien'),
    
    path('bao-cao/lich-su-ca/', api_views.LichSuCaAPIView.as_view(), name='api_lich_su_ca'),
    path('bao-cao/tong-quan-doanh-thu/', api_views.TongQuanDoanhThuAPIView.as_view(), name='api_tong_quan_doanh_thu'),
    
     path('bao-cao/ca/<int:pk>/', api_views.ChiTietCaAPIView.as_view(), name='api_chi_tiet_ca'),
    path('bao-cao/ca/<int:pk>/xuat-excel/', api_views.XuatBaoCaoChiTietCaAPIView.as_view(), name='api_xuat_ca_excel'),
]