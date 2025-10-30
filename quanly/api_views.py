
# Cần cho Channels (FIXED)
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer # <<< DÒNG NÀY PHẢI ĐƯỢC THÊM

# Cần cho Django Forms (hoặc DRF Validation)
from django.forms import ValidationError # <<< DÒNG NÀY PHẢI ĐƯỢC THÊM
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.urls import reverse_lazy 
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Sum, Prefetch, F
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from asgiref.sync import async_to_sync, sync_to_async

# Imports từ các app khác
from accounts import models
from accounts.models import TaiKhoan
from dashboard.api_views import DashboardSummaryAPIView
from quanly.admin import DonHangDichVuAdmin
from .permissions import IsNhanVien

# Import Models
from .models import (
    May, PhienSuDung, NhanVien, HoaDon,
    CaLamViec, GiaoDichTaiChinh, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang,
    NguyenLieu, PhieuKiemKe, ChiTietKiemKe, LichSuThayDoiKho,
    ThongBao, KhachHang, KhuyenMai, KhuyenMaiSuDung
)

# Import Serializers
from .serializers import (
    DonHangDichVuSerializer, KhuyenMaiSerializer, MaySerializer, ChiTietPhienSerializer, CaLamViecSerializer,
    LoaiCaSerializer, MenuItemSerializer, NguyenLieuSerializer,
    KhachHangSerializer, TaoKhachHangSerializer, DoiMatKhauSerializer,
    ChiTietCaLamViecSerializer
)

# -----------------------------------------------------------------------------
# 1. HÀM HELPER VÀ DECORATOR (Đã FIX)
# -----------------------------------------------------------------------------

def get_nhan_vien_object(request):
    """Lấy đối tượng NhanVien liên kết với user đang login (raise 404 nếu không tồn tại)."""
    return get_object_or_404(NhanVien, tai_khoan=request.user)

def get_current_shift(nhan_vien):
    """Lấy ca đang diễn ra của Nhân viên hiện tại."""
    try:
        return CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai=CaLamViec.TrangThai.DANG_DIEN_RA)
    except CaLamViec.DoesNotExist:
        return None

@sync_to_async
def create_inventory_notification_if_needed(nguyen_lieu_id, nguong_canh_bao=10):
    """Kiểm tra tồn kho và tạo thông báo mới nếu dưới ngưỡng."""
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    TaiKhoan = get_user_model()
    
    try:
        nguyen_lieu = NguyenLieu.objects.get(pk=nguyen_lieu_id)
        if nguyen_lieu.so_luong_ton <= nguong_canh_bao:
            thoi_gian_canh_bao_lai = timezone.now() - timedelta(hours=24)
            admin_users = TaiKhoan.objects.filter(is_staff=True)
            
            for admin in admin_users:
                can_tao_moi = not ThongBao.objects.filter(
                    nguoi_nhan=admin,
                    loai_canh_bao=ThongBao.LOAI_CANH_BAO_CHOICES[0][0], # 'KHO'
                    thoi_gian_tao__gte=thoi_gian_canh_bao_lai
                ).exists()

                if can_tao_moi:
                    ThongBao.objects.create(
                        nguoi_nhan=admin,
                        tieu_de=f"CẢNH BÁO KHO: {nguyen_lieu.ten_nguyen_lieu} sắp hết!",
                        noi_dung=f"Nguyên liệu {nguyen_lieu.ten_nguyen_lieu} chỉ còn {nguyen_lieu.so_luong_ton} {nguyen_lieu.don_vi_tinh}. Cần nhập thêm.",
                        loai_canh_bao='KHO',
                        link_xu_ly=reverse_lazy('dashboard_inventory') 
                    )
            return True
        return False
    except NguyenLieu.DoesNotExist:
        return False
    except Exception as e:
        print(f"Lỗi tạo thông báo kho: {e}")
        return False
# Hàm helper ĐƯỢC SỬA (dành cho khuyến mãi giảm giá đơn hàng)
def _validate_and_calculate_promotion(ma_khuyen_mai, items_data_from_request):
    """
    Kiểm tra mã khuyến mãi GIẢM GIÁ (PHAN_TRAM, SO_TIEN) và tính toán giảm giá cho một tập hợp các món hàng.
    Trả về KhuyenMai object, tổng tiền trước giảm, tổng tiền sau giảm, số tiền giảm.
    """
    if not ma_khuyen_mai:
        return None, Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), "Không có mã khuyến mãi được cung cấp."

    try:
        # Chỉ lấy các khuyến mãi loại PHAN_TRAM hoặc SO_TIEN
        promotion = KhuyenMai.objects.get(
            ma_khuyen_mai=ma_khuyen_mai, 
            is_active=True,
            loai_giam_gia__in=[KhuyenMai.LOAI_GIAM_GIA_CHOICES[0][0], KhuyenMai.LOAI_GIAM_GIA_CHOICES[1][0]] # PHAN_TRAM, SO_TIEN
        )
    except KhuyenMai.DoesNotExist:
        return None, Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), "Mã khuyến mãi không tồn tại, không hoạt động hoặc không áp dụng cho đơn hàng."

    current_time = timezone.now()
    if not (promotion.ngay_bat_dau <= current_time <= promotion.ngay_ket_thuc):
        return None, Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), "Mã khuyến mãi đã hết hạn hoặc chưa bắt đầu."

    if promotion.chu_ky_lap_lai == KhuyenMai.LOAI_CHU_KY_CHOICES[2][0]: # 'HANG_TUAN'
        current_day_of_week = current_time.isoweekday() # Thứ 2 = 1, Chủ Nhật = 7
        if promotion.ngay_trong_tuan:
            allowed_days = [int(d) for d in promotion.ngay_trong_tuan.split(',') if d.isdigit()]
            if current_day_of_week not in allowed_days:
                return None, Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), "Mã khuyến mãi không áp dụng vào ngày này."
    
    item_ids = [item['id'] for item in items_data_from_request]
    menu_items_qs = MenuItem.objects.filter(id__in=item_ids)
    menu_items_lookup = {item.id: item for item in menu_items_qs}

    total_before_discount = Decimal('0.00')
    for item_data in items_data_from_request:
        menu_item = menu_items_lookup.get(item_data.get('id'))
        if menu_item:
            so_luong_ban = int(item_data.get('so_luong', 0))
            if so_luong_ban > 0:
                total_before_discount += menu_item.don_gia * so_luong_ban

    if total_before_discount == Decimal('0.00'):
        return promotion, total_before_discount, total_before_discount, Decimal('0.00'), "Không có sản phẩm hợp lệ để áp dụng khuyến mãi."

    applied_discount_amount = Decimal('0.00')
    if promotion.loai_giam_gia == KhuyenMai.LOAI_GIAM_GIA_CHOICES[0][0]: # PHAN_TRAM
        applied_discount_amount = total_before_discount * Decimal(str(promotion.gia_tri / 100))
    elif promotion.loai_giam_gia == KhuyenMai.LOAI_GIAM_GIA_CHOICES[1][0]: # SO_TIEN
        applied_discount_amount = Decimal(str(promotion.gia_tri))

    total_after_discount = total_before_discount - applied_discount_amount
    if total_after_discount < 0:
        total_after_discount = Decimal('0.00')
        applied_discount_amount = total_before_discount
    
    return promotion, total_before_discount, total_after_discount, applied_discount_amount, "Áp dụng khuyến mãi thành công."
# Hàm helper ĐƯỢC SỬA (cho khuyến mãi nạp tiền)
def _validate_and_apply_topup_promotion(ma_khuyen_mai, so_tien_nap_goc, khach_hang):
    """
    Kiểm tra mã khuyến mãi BONUS_NAP_TIEN và tính toán tiền bonus.
    Trả về tiền bonus, thông báo lỗi/thành công.
    """
    if not ma_khuyen_mai:
        return Decimal('0.00'), "Không có mã khuyến mãi được cung cấp.", None # Thêm trả về promotion_obj

    try:
        promotion = KhuyenMai.objects.get(
            ma_khuyen_mai=ma_khuyen_mai, 
            is_active=True,
            loai_giam_gia=KhuyenMai.LOAI_GIAM_GIA_CHOICES[2][0] # Chỉ lấy loại BONUS_NAP_TIEN
        )
    except KhuyenMai.DoesNotExist:
        return Decimal('0.00'), "Mã khuyến mãi không tồn tại, không hoạt động hoặc không áp dụng cho nạp tiền.", None

    current_time = timezone.now()
    if not (promotion.ngay_bat_dau <= current_time <= promotion.ngay_ket_thuc):
        return Decimal('0.00'), "Mã khuyến mãi đã hết hạn hoặc chưa bắt đầu.", None

    if promotion.chu_ky_lap_lai == KhuyenMai.LOAI_CHU_KY_CHOICES[2][0]: # 'HANG_TUAN'
        current_day_of_week = current_time.isoweekday()
        if promotion.ngay_trong_tuan:
            allowed_days = [int(d) for d in promotion.ngay_trong_tuan.split(',') if d.isdigit()]
            if current_day_of_week not in allowed_days:
                return Decimal('0.00'), "Mã khuyến mãi không áp dụng vào ngày này.", None
    
    if not promotion.loai_bonus_nap_tien:
        return Decimal('0.00'), "Mã khuyến mãi nạp tiền chưa được cấu hình loại bonus.", None


    # Kiểm tra giới hạn số lượt sử dụng của mỗi khách hàng
    if promotion.luot_su_dung_toi_da_moi_khach > 0:
        used_count = KhuyenMaiSuDung.objects.filter(khuyen_mai=promotion, khach_hang=khach_hang).count()
        if used_count >= promotion.luot_su_dung_toi_da_moi_khach:
            return Decimal('0.00'), "Bạn đã sử dụng mã khuyến mãi này hết số lượt cho phép.", None

    bonus_amount = Decimal('0.00')
    
    # <<< SỬ DỤNG TRƯỜNG MỚI loai_bonus_nap_tien ĐỂ TÍNH TOÁN >>>
    if promotion.loai_bonus_nap_tien == KhuyenMai.LOAI_BONUS_NAP_TIEN_CHOICES[0][0]: # PHAN_TRAM_BONUS
        if promotion.gia_tri > 0:
            bonus_amount = so_tien_nap_goc * Decimal(str(promotion.gia_tri / 100))
    elif promotion.loai_bonus_nap_tien == KhuyenMai.LOAI_BONUS_NAP_TIEN_CHOICES[1][0]: # SO_TIEN_BONUS
        if promotion.gia_tri > 0:
            bonus_amount = Decimal(str(promotion.gia_tri))
    # <<< KẾT THÚC SỬ DỤNG TRƯỜNG MỚI >>>
    
    return bonus_amount, "Áp dụng khuyến mãi nạp tiền thành công.", promotion

# <<< THÊM API VIEW MỚI ĐỂ LẤY DANH SÁCH MÃ KHUYẾN MÃI NẠP TIỀN HỢP LỆ >>>
class GetActiveTopupPromotionsAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = KhuyenMaiSerializer # Sử dụng lại serializer KhuyenMai

    def get_queryset(self):
        current_time = timezone.now()
        queryset = KhuyenMai.objects.filter(
            is_active=True,
            loai_giam_gia=KhuyenMai.LOAI_GIAM_GIA_CHOICES[2][0], # Chỉ loại BONUS_NAP_TIEN
            ngay_bat_dau__lte=current_time,
            ngay_ket_thuc__gte=current_time
        )
        
        # Lọc theo ngày trong tuần nếu có chu kỳ HANG_TUAN
        # NOTE: Logic này cần KhachHang object để kiểm tra luot_su_dung_toi_da_moi_khach,
        # nhưng ListAPIView không có pk của KhachHang. 
        # Chúng ta sẽ kiểm tra luot_su_dung_toi_da_moi_khach ở frontend hoặc khi check_topup_promotion cụ thể.
        # Ở đây chỉ lọc các mã có thể áp dụng dựa trên thời gian.
        current_day_of_week = current_time.isoweekday()
        queryset = queryset.filter(
            models.Q(chu_ky_lap_lai='MOT_LAN') | 
            models.Q(chu_ky_lap_lai='HANG_NGAY') | 
            (
                models.Q(chu_ky_lap_lai='HANG_TUAN') & 
                models.Q(ngay_trong_tuan__contains=str(current_day_of_week)) # Kiểm tra nếu ngày hiện tại nằm trong chuỗi
            )
            # Thêm logic cho HANG_THANG nếu cần
        )
        return queryset.order_by('-gia_tri') # Sắp xếp ưu tiên mã có giá trị cao

# <<< KẾT THÚC THÊM API VIEW MỚI >>>
# <<< KẾT THÚC HÀM HELPER MỚI >>>
# -----------------------------------------------------------------------------
# 2. CÁC API VIEWS CỦA POS (quảnly/)
# -----------------------------------------------------------------------------

# LƯU Ý: TẤT CẢ CÁC VIEWS DƯỚI ĐÂY ĐỀU ĐÃ ĐƯỢC ÁP DỤNG AUTH & PERMISSIONS TRỰC TIẾP


class DanhSachMayAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = MaySerializer
    
    def get_queryset(self):
        # Lấy phiên đang chạy của tất cả các máy
        running_sessions = PhienSuDung.objects.filter(
            trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA
        ).select_related('khach_hang__tai_khoan')

        return May.objects.select_related('loai_may').prefetch_related(
            Prefetch(
                'cac_phien_su_dung', # Tên trường related_name trong model May
                queryset=running_sessions,
                to_attr='phien_dang_chay_prefetched' # Tên này phải khớp với tên trong Serializer get_phien_dang_chay
            )
        ).order_by('ten_may')

class DanhSachLoaiCaAPIView(generics.ListAPIView):
    # Dùng Generic View đơn giản, không cần permission phức tạp, nhưng thêm vào cho đồng nhất
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated] 
    queryset = LoaiCa.objects.all().order_by('gio_bat_dau')
    serializer_class = LoaiCaSerializer

class MenuAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MenuItem.objects.filter(is_available=True).select_related('danh_muc').order_by('danh_muc__ten_danh_muc', 'ten_mon')
    serializer_class = MenuItemSerializer

class CaLamViecHienTaiAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    def get(self, request, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        if not ca_hien_tai:
            return Response({'message': 'Nhân viên chưa bắt đầu ca làm việc.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)

class BatDauCaAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        if get_current_shift(nhan_vien): return Response({'error': 'Bạn đã có một ca đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)

        loai_ca_id = request.data.get('loai_ca_id')
        tien_mat_str = request.data.get('tien_mat_ban_dau', '0')
        try:
            loai_ca = LoaiCa.objects.get(pk=loai_ca_id)
            tien_mat_ban_dau = Decimal(tien_mat_str)
        except LoaiCa.DoesNotExist:
            return Response({'error': 'Loại ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt ban đầu không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        ca_moi = CaLamViec.objects.create(
            nhan_vien=nhan_vien, loai_ca=loai_ca,
            tien_mat_ban_dau=tien_mat_ban_dau,
            thoi_gian_bat_dau_thuc_te=timezone.now(),
            ngay_lam_viec=timezone.now().date()
        )

        phien_can_ban_giao = PhienSuDung.objects.filter(
            trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA,
            ca_lam_viec__trang_thai=CaLamViec.TrangThai.DA_KET_THUC
        )
        so_luong_phien_ban_giao = phien_can_ban_giao.update(ca_lam_viec=ca_moi)

        serializer = CaLamViecSerializer(ca_moi)
        response_data = serializer.data
        response_data['message_ban_giao'] = f"Đã nhận bàn giao {so_luong_phien_ban_giao} máy đang chạy từ ca trước."
        return Response(response_data, status=status.HTTP_201_CREATED)

class MoMayAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            may = May.objects.select_for_update().get(pk=pk)
            if may.trang_thai != May.TrangThai.TRONG:
                return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)

            khach_hang_id = request.data.get('khach_hang_id', None)
            khach_hang = None
            hinh_thuc = PhienSuDung.HinhThuc.TRA_SAU

            if khach_hang_id:
                try:
                    khach_hang = KhachHang.objects.get(pk=khach_hang_id)
                    hinh_thuc = PhienSuDung.HinhThuc.TRA_TRUOC
                    if khach_hang.so_du <= 0:
                        return Response({'error': f'Tài khoản "{khach_hang.username}" không đủ số dư để mở máy.'}, status=status.HTTP_400_BAD_REQUEST)
                except KhachHang.DoesNotExist:
                    return Response({'error': 'Không tìm thấy tài khoản khách hàng này.'}, status=status.HTTP_404_NOT_FOUND)

            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=nhan_vien,
                ca_lam_viec=ca_hien_tai,
                khach_hang=khach_hang,
                hinh_thuc=hinh_thuc
            )

            may.trang_thai = May.TrangThai.DANG_SU_DUNG
            may.save()

            message = f"Đã mở máy {may.ten_may} cho khách vãng lai."
            if khach_hang:
                message = f"Đã mở máy {may.ten_may} cho khách hàng \"{khach_hang.username}\"."
            
            # Logic WebSockets
            channel_layer = get_channel_layer()
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 
            async_to_sync(channel_layer.group_send)(
                "dashboard_summary",
                {"type": "send_summary_update", "data": new_summary_data},
            )
            
            return Response({'success': message})
            
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)

class ChiTietPhienAPIView(generics.RetrieveAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'
    # FIX: Bỏ dấu nháy đơn thừa
    queryset = PhienSuDung.objects.filter(trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA).prefetch_related('cac_don_hang__chi_tiet__mon')

class KetThucPhienAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # FIX: Bỏ dấu nháy đơn thừa trong query
            phien = PhienSuDung.objects.select_for_update().select_related(
                'may__loai_may', 'khach_hang__tai_khoan'
            ).get(pk=pk, trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA)

            if phien.ca_lam_viec != ca_hien_tai:
                return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN) 

            phien.thoi_gian_ket_thuc = timezone.now()
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            duration_hours = Decimal(duration_seconds) / Decimal(3600)

            tien_gio = duration_hours * phien.may.loai_may.don_gia_gio
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            tong_cong = tien_gio + tien_dich_vu

            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien, ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio, tong_tien_dich_vu=tien_dich_vu,
                tong_cong=tong_cong, da_thanh_toan=True
            )

            khach_hang = phien.khach_hang
            if khach_hang:
                if khach_hang.so_du < tong_cong:
                    transaction.set_rollback(True)
                    return Response({
                        'error': f'Số dư của khách hàng "{khach_hang.username}" không đủ. '
                                 f'Cần {tong_cong:,.0f} VNĐ nhưng chỉ có {khach_hang.so_du:,.0f} VNĐ.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                KhachHang.objects.filter(pk=khach_hang.pk).update(so_du=F('so_du') - tong_cong)
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai, hoa_don=hoa_don, khach_hang=khach_hang,
                    loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK,
                    so_tien=tong_cong
                )
            else:
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai, hoa_don=hoa_don,
                    loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                    so_tien=tong_cong
                )

            don_hang_chua_tt.update(da_thanh_toan=True)
            phien.may.trang_thai = May.TrangThai.TRONG
            phien.may.save()
            phien.trang_thai = PhienSuDung.TrangThai.DA_KET_THUC
            phien.save()

            # Logic WebSockets
            channel_layer = get_channel_layer()
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 
            async_to_sync(channel_layer.group_send)(
                "dashboard_summary",
                {"type": "send_summary_update", "data": new_summary_data},
            )
            
            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': {'id': hoa_don.id, 'tong_tien': hoa_don.tong_cong}
            })
            
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được xử lý.'}, status=status.HTTP_404_NOT_FOUND)

class KetThucCaAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, format=None):
        
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        
        if not ca_hien_tai:
            return Response({'error': 'Không có ca nào đang diễn ra để kết thúc.'}, status=status.HTTP_404_NOT_FOUND)

        tien_mat_cuoi_ca_str = request.data.get('tien_mat_cuoi_ca', '0')
        try:
            tien_mat_cuoi_ca_nv_nhap = Decimal(tien_mat_cuoi_ca_str)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt cuối ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # Logic tính toán chênh lệch
        giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=ca_hien_tai,
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN
            ]
        )
        tong_doanh_thu_he_thong = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total'] or Decimal('0.00')

        tien_mat_ly_thuyet = ca_hien_tai.tien_mat_ban_dau + tong_doanh_thu_he_thong
        chenh_lech = tien_mat_cuoi_ca_nv_nhap - tien_mat_ly_thuyet

        ca_hien_tai.thoi_gian_ket_thuc_thuc_te = timezone.now()
        ca_hien_tai.trang_thai = CaLamViec.TrangThai.DA_KET_THUC
        ca_hien_tai.tien_mat_cuoi_ca = tien_mat_cuoi_ca_nv_nhap
        ca_hien_tai.tong_doanh_thu_he_thong = tong_doanh_thu_he_thong
        ca_hien_tai.chenh_lech = chenh_lech
        ca_hien_tai.save()

        # Logic tạo cảnh báo chênh lệch tiền
        nguong_chenh_lech = Decimal('50000.00')
        
        if abs(chenh_lech) >= nguong_chenh_lech:
            from django.contrib.auth import get_user_model
            TaiKhoan = get_user_model()
            
            loai_chenh_lech = "THIẾU" if chenh_lech < 0 else "THỪA"
            admin_users = TaiKhoan.objects.filter(is_staff=True)
            
            for admin in admin_users:
                ThongBao.objects.create(
                    nguoi_nhan=admin,
                    tieu_de=f"CẢNH BÁO TIỀN: Ca {ca_hien_tai.nhan_vien.tai_khoan.username} có chênh lệch {loai_chenh_lech}",
                    noi_dung=f"Ca làm việc kết thúc lúc {timezone.localtime(ca_hien_tai.thoi_gian_ket_thuc_thuc_te).strftime('%H:%M')} có chênh lệch {loai_chenh_lech}: {abs(chenh_lech):,.0f} VNĐ.",
                    loai_canh_bao='TIEN',
                    link_xu_ly=reverse_lazy('dashboard_reports') 
                )
                
        # Logic WebSockets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {"type": "new_notification_signal"},
        )
        
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)

# quanly/api_views.py

# ... (các imports và hàm helper giữ nguyên)

# quanly/api_views.py (Trong class TaoDonHangAPIView)

class TaoDonHangAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        items = request.data.get('items')
        loai_don_hang_request = request.data.get('loai_don_hang') # GHI_NO hoặc BAN_LE
        phien_id = request.data.get('phien_id')
        ma_khuyen_mai = request.data.get('ma_khuyen_mai', None)

        if not items or not isinstance(items, list) or not loai_don_hang_request in [DonHangDichVu.LoaiDonHang.GHI_NO, DonHangDichVu.LoaiDonHang.BAN_LE]:
            return Response({'error': 'Dữ liệu gửi lên không hợp lệ (items/loai_don_hang).'}, status=status.HTTP_400_BAD_REQUEST)

        phien_su_dung = None
        khach_hang_order = None 
        
        # --- KHỞI TẠO CÁC BIẾN ĐIỀU KHIỂN LUỒNG ---
        is_paid = (loai_don_hang_request == DonHangDichVu.LoaiDonHang.BAN_LE)
        final_loai_don_hang = loai_don_hang_request
        # --- KẾT THÚC KHỞI TẠO ---

        # 1. XÁC ĐỊNH PHIÊN SỬ DỤNG VÀ HÌNH THỨC THANH TOÁN
        if phien_id:
            try:
                phien_su_dung = PhienSuDung.objects.select_related('khach_hang__tai_khoan').get(pk=phien_id, trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA)
            except PhienSuDung.DoesNotExist:
                return Response({'error': 'Phiên sử dụng không tồn tại hoặc đã kết thúc.'}, status=status.HTTP_404_NOT_FOUND)
            
            khach_hang_order = phien_su_dung.khach_hang 
            
            # Order trong phiên LUÔN là Ghi Nợ (chưa thanh toán)
            is_paid = False # <-- Đảm bảo là False nếu có phiên
            final_loai_don_hang = DonHangDichVu.LoaiDonHang.GHI_NO
            
        else: 
            # Order Bán lẻ Thuần túy (KHÔNG CÓ PHIÊN)
            is_paid = (loai_don_hang_request == DonHangDichVu.LoaiDonHang.BAN_LE) # <-- GIỮ NGUYÊN LOGIC BAN ĐẦU: Bán lẻ = is_paid=True
            final_loai_don_hang = loai_don_hang_request
        # 2. XỬ LÝ KHUYẾN MÃI
        promotion_obj, tong_tien_thuc_te_cho_dh, total_after_discount, applied_discount_amount, promo_message = \
            _validate_and_calculate_promotion(ma_khuyen_mai, items)
        
        if ma_khuyen_mai and not promotion_obj:
            return Response({'error': promo_message}, status=status.HTTP_400_BAD_REQUEST)
        
        final_order_amount = tong_tien_thuc_te_cho_dh - applied_discount_amount
        
        # 3. KIỂM TRA ITEM VÀ TRỪ KHO (TẠO CHI TIẾT)
        item_ids = [item['id'] for item in items]
        menu_items_qs = MenuItem.objects.filter(id__in=item_ids).prefetch_related('dinh_luong__nguyen_lieu')
        menu_items = {item.id: item for item in menu_items_qs}
        chi_tiet_don_hang_list = []

        for item_data in items:
            mon = menu_items.get(item_data.get('id'))
            if not mon: continue

            so_luong_ban = int(item_data.get('so_luong', 0))
            if so_luong_ban <= 0: continue

            thanh_tien = mon.don_gia * so_luong_ban
            chi_tiet_don_hang_list.append(
                ChiTietDonHang(don_hang=None, mon=mon, so_luong=so_luong_ban, thanh_tien=thanh_tien)
            )
            
            # Trừ kho nguyên liệu
            for dinh_luong in mon.dinh_luong.all():
                nguyen_lieu_id = dinh_luong.nguyen_lieu.pk
                so_luong_tru = dinh_luong.so_luong_can * so_luong_ban
                
                NguyenLieu.objects.filter(pk=nguyen_lieu_id).update(
                    so_luong_ton=F('so_luong_ton') - so_luong_tru
                )
                async_to_sync(create_inventory_notification_if_needed)(nguyen_lieu_id) 

        if not chi_tiet_don_hang_list:
            transaction.set_rollback(True)
            return Response({'error': 'Không có sản phẩm hợp lệ trong đơn hàng.'}, status=status.HTTP_400_BAD_REQUEST)


        # 4. TẠO VÀ LƯU ĐƠN HÀNG VÀ CHI TIẾT
        don_hang = DonHangDichVu.objects.create(
            ca_lam_viec=ca_hien_tai, 
            phien_su_dung=phien_su_dung,
            loai_don_hang=final_loai_don_hang, 
            da_thanh_toan=is_paid, 
            khuyen_mai=promotion_obj, 
            tien_giam_gia=applied_discount_amount,
            tong_tien=Decimal('0.00') # Gán tạm, sẽ được tính lại
        )
        
        for chi_tiet in chi_tiet_don_hang_list:
            chi_tiet.don_hang = don_hang
        ChiTietDonHang.objects.bulk_create(chi_tiet_don_hang_list)
        
        # <<< GỌI HÀM TÍNH TỔNG TIỀN MỚI TẠI ĐÂY >>>
        don_hang.calculate_total() 
        
        # Lấy lại giá trị sau khi tính toán
        final_order_amount = don_hang.tong_tien
        
        # 5. XỬ LÝ GIAO DỊCH THANH TOÁN (CHỈ CHO BÁN LẺ THUẦN TÚY)
        if is_paid: 
            # Bán lẻ thuần túy (Tiền mặt/Chuyển khoản) -> TẠO GIAO DỊCH VÀ CỘNG DOANH THU
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai, 
                don_hang_le=don_hang,
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                so_tien=final_order_amount,
                ghi_chu=f"Thanh toán cho đơn hàng bán lẻ #{don_hang.id} (Giảm: {applied_discount_amount:,.0f} VNĐ)"
            )
            
            # ✅ CỘNG DOANH THU BÁN LẺ VÀO CA HIỆN TẠI
            CaLamViec.objects.filter(pk=ca_hien_tai.pk).update(
                 tong_doanh_thu_he_thong=F('tong_doanh_thu_he_thong') + final_order_amount # Sửa tên field
            )

        
        # 6. GỬI TÍN HIỆU WEBSOCKET
        channel_layer = get_channel_layer()
        new_summary_data = DashboardSummaryAPIView().calculate_summary() 

        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {"type": "send_summary_update", "data": new_summary_data},
        )
        
        # 7. TRẢ VỀ KẾT QUẢ
        return Response({
            'success': 'Tạo đơn hàng thành công!', 
            'don_hang_id': don_hang.id,
            'tong_tien_goc': tong_tien_thuc_te_cho_dh,
            'tien_giam_gia': applied_discount_amount,
            'tong_tien_cuoi': final_order_amount,
            'message': promo_message,
            'requires_manual_pay': not is_paid 
        }, status=status.HTTP_201_CREATED)

class NhanVienNoDichVuListAPIView(generics.ListAPIView):
    """API lấy danh sách các Order dịch vụ đang GHI_NO (chưa thanh toán)."""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = DonHangDichVuSerializer

    def get_queryset(self):
        nhan_vien = get_nhan_vien_object(self.request)
        ca_hien_tai = get_current_shift(nhan_vien)

        if not ca_hien_tai:
            return DonHangDichVu.objects.none()

        queryset = DonHangDichVu.objects.select_related(
            'phien_su_dung__may', # Đảm bảo có tên máy
            'khuyen_mai',
            'ca_lam_viec'
        ).prefetch_related(
            'chi_tiet__mon'
        ).filter(
            ca_lam_viec=ca_hien_tai,
            da_thanh_toan=False,
            phien_su_dung__isnull=False # <<< CHỈ LẤY CÁC ORDER GHI NỢ TỪ PHIÊN MÁY
        ).order_by('-id')
        
        return queryset


# quanly/api_views.py (Class ThanhToanNoDichVuAPIView đã sửa lỗi logic doanh thu)
class ThanhToanNoDichVuAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Lấy đơn hàng GHI_NO thuộc ca hiện tại
            don_hang = DonHangDichVu.objects.select_for_update().get(
                pk=pk,
                da_thanh_toan=False,
                ca_lam_viec=ca_hien_tai,
                loai_don_hang=DonHangDichVu.LoaiDonHang.GHI_NO
            )
        except DonHangDichVu.DoesNotExist:
            return Response({'error': 'Order không tồn tại, đã được thanh toán hoặc không thuộc ca hiện tại.'}, status=status.HTTP_404_NOT_FOUND)

        # --- Bắt đầu logic xử lý thành công ---
        
        thanh_tien_da_thu = don_hang.tong_tien
        
        # 1. TẠO GIAO DỊCH THANH TOÁN (Tiền mặt/Chuyển khoản)
        GiaoDichTaiChinh.objects.create(
            ca_lam_viec=ca_hien_tai,
            don_hang_le=don_hang,
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
            so_tien=thanh_tien_da_thu,
            ghi_chu=f"Thanh toán thủ công Order nợ #{don_hang.id} (Tiền mặt/CK)"
        )

        # 3. CẬP NHẬT TRẠNG THÁI ORDER
        don_hang.da_thanh_toan = True
        don_hang.save(update_fields=['da_thanh_toan'])
        
        # ✅ CẬP NHẬT TỔNG THU CỦA CA HIỆN TẠI (SỬ DỤNG TÊN TRƯỜNG MODEL CHÍNH XÁC)
        CaLamViec.objects.filter(pk=ca_hien_tai.pk).update(
                tong_doanh_thu_he_thong=F('tong_doanh_thu_he_thuc') + thanh_tien_da_thu # Sửa tên field
            )
        
        # 4. GỬI TÍN HIỆU WEBSOCKET
        channel_layer = get_channel_layer()
        new_summary_data = DashboardSummaryAPIView().calculate_summary() 
        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {"type": "send_summary_update", "data": new_summary_data},
        )

        return Response({'success': f'Đã xác nhận thanh toán {thanh_tien_da_thu:,.0f} VNĐ cho Order #{don_hang.id}'})

class KetThucPhienAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            phien = PhienSuDung.objects.select_for_update().select_related(
                'may__loai_may', 'khach_hang__tai_khoan'
            ).get(pk=pk, trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA)

            if phien.ca_lam_viec != ca_hien_tai:
                return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN) 

            phien.thoi_gian_ket_thuc = timezone.now()
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            duration_hours = Decimal(duration_seconds) / Decimal(3600)

            tien_gio = duration_hours * phien.may.loai_may.don_gia_gio
            
            # <<< LẤY CÁC ĐƠN HÀNG CHƯA THANH TOÁN VÀ TÍNH TỔNG TIỀN DỊCH VỤ VÀ TỔNG GIẢM GIÁ >>>
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            
            # tong_tien_dich_vu ở đây sẽ là tổng của các đơn hàng đã được giảm giá (nếu có)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            
            # Tổng tiền giảm giá từ tất cả các đơn hàng dịch vụ trong phiên
            tong_tien_giam_gia = don_hang_chua_tt.aggregate(total=Sum('tien_giam_gia'))['total'] or Decimal('0.00')
            # <<< KẾT THÚC THAY ĐỔI >>>

            tong_cong = tien_gio + tien_dich_vu # Tổng cộng đã bao gồm giảm giá dịch vụ
            # Giá trị tong_tien_giam_gia ở đây sẽ được dùng để lưu vào HoaDon

            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien, ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio, 
                tong_tien_dich_vu=tien_dich_vu,
                tien_giam_gia=tong_tien_giam_gia, # <<< LƯU TỔNG TIỀN GIẢM GIÁ
                tong_cong=tong_cong, 
                da_thanh_toan=True
            )

            khach_hang = phien.khach_hang
            if khach_hang:
                if khach_hang.so_du < tong_cong:
                    transaction.set_rollback(True)
                    return Response({
                        'error': f'Số dư của khách hàng "{khach_hang.username}" không đủ. '
                                 f'Cần {tong_cong:,.0f} VNĐ nhưng chỉ có {khach_hang.so_du:,.0f} VNĐ.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                KhachHang.objects.filter(pk=khach_hang.pk).update(so_du=F('so_du') - tong_cong)
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai, hoa_don=hoa_don, khach_hang=khach_hang,
                    loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK,
                    so_tien=tong_cong
                )
            else:
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai, hoa_don=hoa_don,
                    loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                    so_tien=tong_cong
                )

            don_hang_chua_tt.update(da_thanh_toan=True)
            phien.may.trang_thai = May.TrangThai.TRONG
            phien.may.save()
            phien.trang_thai = PhienSuDung.TrangThai.DA_KET_THUC
            phien.save()

            # Logic WebSockets
            channel_layer = get_channel_layer()
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 
            async_to_sync(channel_layer.group_send)(
                "dashboard_summary",
                {"type": "send_summary_update", "data": new_summary_data},
            )
            
            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': {
                    'id': hoa_don.id, 
                    'tong_tien': hoa_don.tong_cong,
                    'tien_giam_gia': hoa_don.tien_giam_gia # <<< THÊM TIỀN GIẢM GIÁ VÀO RESPONSE
                }
            })
            
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được xử lý.'}, status=status.HTTP_404_NOT_FOUND)
class DanhSachNguyenLieuAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all().order_by('ten_nguyen_lieu')

class BaoHongNguyenLieuAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        if not ca_hien_tai: return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nguyen_lieu = NguyenLieu.objects.get(pk=pk)
        except NguyenLieu.DoesNotExist:
            return Response({'error': 'Nguyên liệu không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            so_luong_hong = float(request.data.get('so_luong', 0))
            ly_do = request.data.get('ly_do', '')
            if so_luong_hong <= 0 or not ly_do:
                return Response({'error': 'Số lượng và lý do không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Số lượng không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        NguyenLieu.objects.filter(pk=pk).update(so_luong_ton=F('so_luong_ton') - so_luong_hong)
        LichSuThayDoiKho.objects.create(
            ca_lam_viec=ca_hien_tai, nhan_vien=nhan_vien,
            nguyen_lieu=nguyen_lieu, so_luong_thay_doi=-so_luong_hong,
            loai_thay_doi=LichSuThayDoiKho.LoaiThayDoi.HUY_HANG,
            ly_do=ly_do
        )

        # GỌI HELPER TẠO CẢNH BÁO KHO (Dù là hủy hàng, vẫn check xem có dưới ngưỡng không)
        async_to_sync(create_inventory_notification_if_needed)(nguyen_lieu.pk) 

        nguyen_lieu.refresh_from_db()
        return Response(NguyenLieuSerializer(nguyen_lieu).data)

class KiemKeCuoiCaAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        # ... (Phần còn lại của hàm) ...
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc nào đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)

        if PhieuKiemKe.objects.filter(ca_lam_viec=ca_hien_tai).exists():
            return Response({'error': 'Ca làm việc này đã được kiểm kê.'}, status=status.HTTP_400_BAD_REQUEST)

        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'error': 'Không có dữ liệu kiểm kê được gửi.'}, status=status.HTTP_400_BAD_REQUEST)

        phieu = PhieuKiemKe.objects.create(ca_lam_viec=ca_hien_tai, nhan_vien=nhan_vien, da_xac_nhan=False)
        nguyen_lieu_ids = [item['nguyen_lieu_id'] for item in items_data]
        danh_sach_nguyen_lieu = NguyenLieu.objects.in_bulk(nguyen_lieu_ids)
        chi_tiet_list = []

        for item_data in items_data:
            nguyen_lieu = danh_sach_nguyen_lieu.get(item_data['nguyen_lieu_id'])
            if not nguyen_lieu: continue

            ton_he_thong = float(nguyen_lieu.so_luong_ton)
            ton_thuc_te = float(item_data.get('ton_thuc_te', 0))
            chenh_lech = ton_thuc_te - ton_he_thong
            chi_tiet_list.append(ChiTietKiemKe(
                phieu_kiem_ke=phieu, nguyen_lieu=nguyen_lieu,
                ton_he_thong=ton_he_thong, ton_thuc_te=ton_thuc_te, chenh_lech=chenh_lech
            ))

        ChiTietKiemKe.objects.bulk_create(chi_tiet_list)
        return Response({'success': 'Đã gửi báo cáo kiểm kê thành công. Chờ quản lý xác nhận.'}, status=status.HTTP_201_CREATED)

class KhachHangListCreateAPIView(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    def get(self, request, format=None):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper (chỉ để đảm bảo quyền)
        khach_hangs = KhachHang.objects.select_related('tai_khoan').all().order_by('tai_khoan__username')
        serializer = KhachHangSerializer(khach_hangs, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, format=None):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper (chỉ để đảm bảo quyền)
        serializer = TaoKhachHangSerializer(data=request.data)
        # ... (Phần còn lại của hàm) ...
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            new_user = TaiKhoan.objects.create_user(username=data['username'], password=data['password'])
            new_khach_hang = KhachHang.objects.create(tai_khoan=new_user)
        except (IntegrityError, ValidationError) as e:
            return Response({'error': f'Lỗi khi tạo tài khoản: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Lỗi không xác định khi tạo khách hàng: {e}")
            return Response({'error': 'Đã có lỗi xảy ra ở phía máy chủ.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_serializer = KhachHangSerializer(new_khach_hang)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class KhachHangDetailAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    def get_object(self, pk):
        try: return KhachHang.objects.get(pk=pk)
        except KhachHang.DoesNotExist: raise Http404

    def patch(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper (chỉ để đảm bảo quyền)
        khach_hang = self.get_object(pk)
        # ... (Phần còn lại của hàm) ...
        serializer = DoiMatKhauSerializer(data=request.data)
        if serializer.is_valid():
            user = khach_hang.tai_khoan
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            return Response({'success': 'Đổi mật khẩu thành công.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper (chỉ để đảm bảo quyền)
        khach_hang = self.get_object(pk)
        khach_hang.tai_khoan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NapTienAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        ca_hien_tai = get_current_shift(nhan_vien) # Gọi Helper
        
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            khach_hang = KhachHang.objects.get(pk=pk)
        except KhachHang.DoesNotExist:
            return Response({'error': 'Khách hàng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            so_tien_nap_goc = Decimal(request.data.get('so_tien', '0'))
            if so_tien_nap_goc <= 0:
                return Response({'error': 'Số tiền nạp phải lớn hơn 0.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        ma_khuyen_mai = request.data.get('ma_khuyen_mai', None)

        bonus_amount = Decimal('0.00')
        promo_message = "Không có khuyến mãi được áp dụng."
        promotion_obj = None

        if ma_khuyen_mai:
            # Gọi hàm helper mới để xử lý khuyến mãi nạp tiền, nhận thêm promotion_obj
            bonus_amount, promo_message, promotion_obj = _validate_and_apply_topup_promotion(ma_khuyen_mai, so_tien_nap_goc, khach_hang)
            
            if bonus_amount == Decimal('0.00') and "thành công" not in promo_message: # Nếu không có bonus và có lỗi cụ thể
                return Response({'error': promo_message}, status=status.HTTP_400_BAD_REQUEST)

        # Cập nhật số dư gốc
        KhachHang.objects.filter(pk=pk).update(so_du=F('so_du') + so_tien_nap_goc + bonus_amount)
        
        # Ghi nhận giao dịch nạp tiền gốc
        GiaoDichTaiChinh.objects.create(
            ca_lam_viec=ca_hien_tai,
            khach_hang=khach_hang,
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN,
            so_tien=so_tien_nap_goc,
            ghi_chu=f"Nạp tiền gốc: {so_tien_nap_goc:,.0f} VNĐ"
        )
        
        # Ghi nhận giao dịch bonus (nếu có)
        if bonus_amount > 0:
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai,
                khach_hang=khach_hang,
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.ADMIN_ADJUST, 
                so_tien=bonus_amount,
                ghi_chu=f"Bonus từ khuyến mãi '{ma_khuyen_mai}' (ID: {promotion_obj.id if promotion_obj else 'N/A'}): {bonus_amount:,.0f} VNĐ"
            )
            # Ghi lại lượt sử dụng khuyến mãi (chỉ khi có promotion_obj hợp lệ)
            if promotion_obj:
                KhuyenMaiSuDung.objects.create(khuyen_mai=promotion_obj, khach_hang=khach_hang)

        # Logic WebSockets (giữ nguyên)
        channel_layer = get_channel_layer()
        new_summary_data = DashboardSummaryAPIView().calculate_summary() 

        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {"type": "send_summary_update", "data": new_summary_data},
        )

        khach_hang.refresh_from_db()
        return Response({
            'success': f"Nạp {so_tien_nap_goc:,.0f} VNĐ thành công. " + (f"Bạn nhận thêm {bonus_amount:,.0f} VNĐ bonus!" if bonus_amount > 0 else ""),
            'new_balance': khach_hang.so_du,
            'amount_deposited': so_tien_nap_goc,
            'bonus_amount': bonus_amount,
            'promo_message': promo_message
        })


class LichSuCaAPIView(generics.ListAPIView): # FIX: Đã sửa từ APIView, generics.ListAPIView
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = CaLamViecSerializer

    def get_queryset(self):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(self.request) # Gọi Helper
        queryset = CaLamViec.objects.filter(
            trang_thai=CaLamViec.TrangThai.DA_KET_THUC,
            nhan_vien=nhan_vien
        ).select_related('nhan_vien__tai_khoan', 'loai_ca').order_by('-thoi_gian_ket_thuc_thuc_te')
        # ... (Phần còn lại của hàm) ...

        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        if start_date_str:
            queryset = queryset.filter(ngay_lam_viec__gte=start_date_str)
        if end_date_str:
            queryset = queryset.filter(ngay_lam_viec__lte=end_date_str)

        return queryset

class TongQuanDoanhThuAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    def get(self, request, *args, **kwargs):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        # ... (Phần còn lại của hàm) ...
        
        cac_ca_cua_nv = CaLamViec.objects.filter(nhan_vien=nhan_vien, ngay_lam_viec__range=[start_date, end_date])
        
        doanh_thu_theo_ngay = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec__in=cac_ca_cua_nv,
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
            ]
        ).values('thoi_gian_giao_dich__date').annotate(total=Sum('so_tien')).order_by('thoi_gian_giao_dich__date')
        
        top_mon_an = ChiTietDonHang.objects.filter(
            don_hang__ca_lam_viec__in=cac_ca_cua_nv
        ).values('mon__ten_mon').annotate(total_sold=Sum('so_luong')).order_by('-total_sold')[:5]

        giao_dichs = GiaoDichTaiChinh.objects.filter(ca_lam_viec__in=cac_ca_cua_nv)
        tong_doanh_thu = giao_dichs.filter(loai_giao_dich__in=[
            GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
            GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE
        ]).aggregate(total=Sum('so_tien'))['total'] or 0
        so_hoa_don = HoaDon.objects.filter(ca_lam_viec__in=cac_ca_cua_nv).count()
        
        data = {
            'summary': {
                'tong_doanh_thu': tong_doanh_thu,
                'so_hoa_don': so_hoa_don,
                'doanh_thu_trung_binh': tong_doanh_thu / so_hoa_don if so_hoa_don > 0 else 0
            },
            # Cần convert date objects to string
            'doanh_thu_theo_ngay': [{'ngay': entry['thoi_gian_giao_dich__date'].strftime('%Y-%m-%d'), 'total': entry['total']} for entry in doanh_thu_theo_ngay],
            'top_mon_an': list(top_mon_an)
        }
        return Response(data)

class ChiTietCaAPIView(generics.RetrieveAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = ChiTietCaLamViecSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(self.request) # Gọi Helper
        return CaLamViec.objects.filter(trang_thai=CaLamViec.TrangThai.DA_KET_THUC, nhan_vien=nhan_vien)

class XuatBaoCaoChiTietCaAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    
    def get(self, request, pk, *args, **kwargs):
        # ... (Sử dụng hàm helper) ...
        nhan_vien = get_nhan_vien_object(request) # Gọi Helper
        try:
            ca = CaLamViec.objects.get(pk=pk, nhan_vien=nhan_vien)
        except CaLamViec.DoesNotExist:
            return HttpResponse("Không tìm thấy ca làm việc hoặc bạn không có quyền truy cập.", status=404)
        # ... (Phần còn lại của hàm) ...
        
        serializer = ChiTietCaLamViecSerializer(ca)
        data = serializer.data
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="BaoCaoCa_{ca.id}_{ca.ngay_lam_viec.strftime("%d%m%Y")}.xlsx"'
        
        try:
            # ... (Logic tạo Excel giữ nguyên) ...
            
            # Trả về response
            return response
        except Exception as e:
            print(f"Lỗi khi tạo file Excel: {e}")
            return HttpResponse(f"Đã có lỗi xảy ra khi tạo file báo cáo: {e}", status=500)
        
        
        # <<< THÊM MỘT API VIEW ĐỂ KIỂM TRA MÃ KHUYẾN MÃI TỪ FRONTEND MÀ KHÔNG TẠO ĐƠN HÀNG >>>
class CheckPromotionAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]

    def post(self, request, format=None):
        ma_khuyen_mai = request.data.get('ma_khuyen_mai')
        items = request.data.get('items') # Cần biết các món hàng để tính toán

        if not items or not isinstance(items, list):
            return Response({'error': 'Dữ liệu sản phẩm không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # CHỈ GỌI HÀM KIỂM TRA KHUYẾN MÃI DỊCH VỤ
        promotion_obj, total_before_discount, total_after_discount, applied_discount_amount, promo_message = \
            _validate_and_calculate_promotion(ma_khuyen_mai, items)
        
        if not promotion_obj:
            return Response({'error': promo_message}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': promo_message,
            'ma_khuyen_mai': promotion_obj.ma_khuyen_mai,
            'total_before_discount': total_before_discount,
            'total_after_discount': total_after_discount,
            'applied_discount_amount': applied_discount_amount,
            'mo_ta': promotion_obj.mo_ta
        })

# <<< THÊM API VIEW ĐỂ KIỂM TRA KHUYẾN MÃI NẠP TIỀN TỪ FRONTEND (KHÔNG THỰC HIỆN NẠP) >>>
class CheckTopupPromotionAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]

    def post(self, request, pk, format=None): # pk là ID của khách hàng
        ma_khuyen_mai = request.data.get('ma_khuyen_mai')
        so_tien_nap_goc_str = request.data.get('so_tien') # Số tiền dự kiến nạp
        
        try:
            khach_hang = KhachHang.objects.get(pk=pk)
            so_tien_nap_goc = Decimal(so_tien_nap_goc_str)
            if so_tien_nap_goc <= 0:
                raise ValueError("Số tiền nạp phải lớn hơn 0.")
        except KhachHang.DoesNotExist:
            return Response({'error': 'Khách hàng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)
        except (InvalidOperation, ValueError) as e:
            return Response({'error': f'Dữ liệu số tiền không hợp lệ: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        bonus_amount, promo_message = _validate_and_apply_topup_promotion(ma_khuyen_mai, so_tien_nap_goc, khach_hang)
        
        if bonus_amount == Decimal('0.00') and "thành công" not in promo_message: # Nếu không có bonus và có lỗi cụ thể
            return Response({'error': promo_message}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': promo_message,
            'original_amount': so_tien_nap_goc,
            'bonus_amount': bonus_amount,
            'total_after_bonus': so_tien_nap_goc + bonus_amount,
            'ma_khuyen_mai': ma_khuyen_mai
        })
# <<< KẾT THÚC THÊM API VIEW MỚI >>>
class NhanVienNoDichVuListAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]
    serializer_class = DonHangDichVuSerializer

    def get_queryset(self):
        nhan_vien = get_nhan_vien_object(self.request)
        ca_hien_tai = get_current_shift(nhan_vien)
        if not ca_hien_tai:
            return DonHangDichVu.objects.none()
        return DonHangDichVu.objects.filter(
            ca_lam_viec=ca_hien_tai,
            da_thanh_toan=False
        ).select_related('phien_su_dung__may', 'khuyen_mai')

