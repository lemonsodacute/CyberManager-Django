# quanly/api_views.py

from datetime import datetime, timedelta
from os import truncate
from django.forms import ValidationError
from django.urls import reverse_lazy
import pandas as pd
from accounts.models import TaiKhoan
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Sum, Prefetch, F
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse
from .serializers import ChiTietCaLamViecSerializer
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
# Cần import cho Channels
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Cần import API View từ ứng dụng Dashboard
from dashboard.api_views import DashboardSummaryAPIView
# Import Quyền tùy chỉnh
from .permissions import IsNhanVien
from .models import KhachHang, ThongBao, NguyenLieu 
from asgiref.sync import async_to_sync, sync_to_async 
# Import Models
from .models import (
    May, PhienSuDung, NhanVien, HoaDon,
    CaLamViec, GiaoDichTaiChinh, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang,
    NguyenLieu, PhieuKiemKe, ChiTietKiemKe, LichSuThayDoiKho,
    KhachHang
)

# Import Serializers
from .serializers import (
    MaySerializer,
    ChiTietPhienSerializer,
    CaLamViecSerializer,
    LoaiCaSerializer,
    MenuItemSerializer,
    NguyenLieuSerializer,
    KhachHangSerializer,
    TaoKhachHangSerializer,
    DoiMatKhauSerializer
)

@sync_to_async
def create_inventory_notification_if_needed(nguyen_lieu_id, nguong_canh_bao=10):
    """Kiểm tra tồn kho và tạo thông báo mới nếu dưới ngưỡng (Hàm Helper)."""
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
# -----------------------------------------------------------------------------
# LỚP CHA
# -----------------------------------------------------------------------------
class BaseNhanVienAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsNhanVien]  # <<< SỬ DỤNG CLASS ĐÃ FIX

    def get_nhan_vien(self, request):
            # Thêm kiểm tra ở đây để tránh lỗi khi người dùng không có object nhanvien
        try:
            return request.user.nhanvien
        except:
            # Nếu không có object nhanvien (chỉ là is_staff=True mà thôi)
            return None 
    def get_ca_hien_tai(self, nhan_vien):
        try:
            return CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai=CaLamViec.TrangThai.DANG_DIEN_RA)
        except CaLamViec.DoesNotExist:
            return None

# -----------------------------------------------------------------------------
# CÁC API VIEW
# -----------------------------------------------------------------------------

class DanhSachMayAPIView(generics.ListAPIView):
    serializer_class = MaySerializer
    def get_queryset(self):
        return May.objects.select_related('loai_may').prefetch_related(
            Prefetch(
                'cac_phien_su_dung',
                queryset=PhienSuDung.objects.filter(trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA).order_by('-thoi_gian_bat_dau'),
                to_attr='phien_dang_chay_prefetched'
            )
        ).order_by('ten_may')

class DanhSachLoaiCaAPIView(generics.ListAPIView):
    queryset = LoaiCa.objects.all().order_by('gio_bat_dau')
    serializer_class = LoaiCaSerializer

class MenuAPIView(generics.ListAPIView):
    queryset = MenuItem.objects.filter(is_available=True).select_related('danh_muc').order_by('danh_muc__ten_danh_muc', 'ten_mon')
    serializer_class = MenuItemSerializer

class CaLamViecHienTaiAPIView(BaseNhanVienAPIView):
    def get(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'message': 'Nhân viên chưa bắt đầu ca làm việc.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)

class BatDauCaAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if self.get_ca_hien_tai(nhan_vien): return Response({'error': 'Bạn đã có một ca đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)

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

class MoMayAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
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
            
            
            # **********************************************
            # <<< BƯỚC MỚI: GỬI THÔNG ĐIỆP WEBSOCKET >>>
            # **********************************************
            
            channel_layer = get_channel_layer()
            
            # Lấy dữ liệu tổng quan mới nhất sau khi mở máy
            # Gọi hàm helper đã tách ra từ DashboardSummaryAPIView
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 

            async_to_sync(channel_layer.group_send)(
                "dashboard_summary", # Tên group
                {
                    "type": "send_summary_update", # Tên hàm trong Consumer (dashboard/consumers.py)
                    "data": new_summary_data,
                },
            )
            # **********************************************
            
            return Response({'success': message})
            
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
class ChiTietPhienAPIView(generics.RetrieveAPIView):
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'
    queryset = PhienSuDung.objects.filter(trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA).prefetch_related('cac_don_hang__chi_tiet__mon')
class KetThucPhienAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
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

            # **********************************************
            # <<< GỬI THÔNG ĐIỆP WEBSOCKET >>>
            # **********************************************
            channel_layer = get_channel_layer()
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 

            async_to_sync(channel_layer.group_send)(
                "dashboard_summary",
                {
                    "type": "send_summary_update",
                    "data": new_summary_data,
                },
            )
            # **********************************************

            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': {'id': hoa_don.id, 'tong_tien': hoa_don.tong_cong}
            })
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được xử lý.'}, status=status.HTTP_404_NOT_FOUND)
class KetThucCaAPIView(BaseNhanVienAPIView):
   # quanly/api_views.py - Trong class KetThucCaAPIView
# ...
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca nào đang diễn ra để kết thúc.'}, status=status.HTTP_404_NOT_FOUND)

        tien_mat_cuoi_ca_str = request.data.get('tien_mat_cuoi_ca', '0')
        try:
            tien_mat_cuoi_ca_nv_nhap = Decimal(tien_mat_cuoi_ca_str)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt cuối ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

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

        # **********************************************
        # <<< LOGIC TẠO CẢNH BÁO CHÊNH LỆCH TIỀN >>>
        # **********************************************
        nguong_chenh_lech = Decimal('50000.00') # Ngưỡng 50,000 VNĐ
        
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
                
        # **********************************************
        # <<< GỬI TÍN HIỆU WEBSOCKET (MỚI) >>>
        # **********************************************
        channel_layer = get_channel_layer()
        
        # Gửi tín hiệu mới để Frontend biết có thông báo mới (và có thể là cập nhật summary dashboard)
        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {
                "type": "new_notification_signal", 
            },
        )
        # **********************************************
        
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)
class TaoDonHangAPIView(BaseNhanVienAPIView):
# quanly/api_views.py - Trong class TaoDonHangAPIView
# ...
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        items = request.data.get('items')
        loai_don_hang = request.data.get('loai_don_hang')
        phien_id = request.data.get('phien_id')

        if not items or not isinstance(items, list) or not loai_don_hang in [DonHangDichVu.LoaiDonHang.GHI_NO, DonHangDichVu.LoaiDonHang.BAN_LE]:
            return Response({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        phien_su_dung = None
        if loai_don_hang == DonHangDichVu.LoaiDonHang.GHI_NO:
            if not phien_id:
                return Response({'error': 'Cần cung cấp ID của phiên để ghi nợ.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                phien_su_dung = PhienSuDung.objects.get(pk=phien_id, trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA)
            except PhienSuDung.DoesNotExist:
                return Response({'error': 'Phiên sử dụng không tồn tại hoặc đã kết thúc.'}, status=status.HTTP_404_NOT_FOUND)

        don_hang = DonHangDichVu.objects.create(
            ca_lam_viec=ca_hien_tai, phien_su_dung=phien_su_dung,
            loai_don_hang=loai_don_hang,
            da_thanh_toan=(loai_don_hang == DonHangDichVu.LoaiDonHang.BAN_LE)
        )

        tong_tien = Decimal('0.00')
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
                ChiTietDonHang(don_hang=don_hang, mon=mon, so_luong=so_luong_ban, thanh_tien=thanh_tien)
            )
            tong_tien += thanh_tien

            # Trừ kho nguyên liệu
            for dinh_luong in mon.dinh_luong.all():
                nguyen_lieu_id = dinh_luong.nguyen_lieu.pk
                so_luong_tru = dinh_luong.so_luong_can * so_luong_ban
                
                NguyenLieu.objects.filter(pk=nguyen_lieu_id).update(
                    so_luong_ton=F('so_luong_ton') - so_luong_tru
                )
                
                # **********************************************
                # <<< GỌI HELPER TẠO CẢNH BÁO KHO >>>
                # **********************************************
                async_to_sync(create_inventory_notification_if_needed)(nguyen_lieu_id) 

        if not chi_tiet_don_hang_list:
            transaction.set_rollback(True)
            return Response({'error': 'Không có sản phẩm hợp lệ trong đơn hàng.'}, status=status.HTTP_400_BAD_REQUEST)

        ChiTietDonHang.objects.bulk_create(chi_tiet_don_hang_list)
        don_hang.tong_tien = tong_tien
        don_hang.save()

        if loai_don_hang == DonHangDichVu.LoaiDonHang.BAN_LE:
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai, don_hang_le=don_hang,
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                so_tien=tong_tien,
                ghi_chu=f"Thanh toán cho đơn hàng bán lẻ #{don_hang.id}"
            )
        
        # **********************************************
        # <<< GỬI TÍN HIỆU WEBSOCKET CHUNG >>>
        # **********************************************
        if loai_don_hang == DonHangDichVu.LoaiDonHang.BAN_LE: 
            channel_layer = get_channel_layer()
            new_summary_data = DashboardSummaryAPIView().calculate_summary() 

            async_to_sync(channel_layer.group_send)(
                "dashboard_summary",
                {
                    "type": "send_summary_update",
                    "data": new_summary_data,
                },
            )
        # **********************************************

        return Response({'success': 'Tạo đơn hàng thành công!', 'don_hang_id': don_hang.id}, status=status.HTTP_201_CREATED)
class DanhSachNguyenLieuAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all().order_by('ten_nguyen_lieu')

class BaoHongNguyenLieuAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
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

        nguyen_lieu.refresh_from_db()
        return Response(NguyenLieuSerializer(nguyen_lieu).data)

class KiemKeCuoiCaAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
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

class KhachHangListCreateAPIView(BaseNhanVienAPIView):
    def get(self, request, format=None):
        khach_hangs = KhachHang.objects.select_related('tai_khoan').all().order_by('tai_khoan__username')
        serializer = KhachHangSerializer(khach_hangs, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, format=None):
        serializer = TaoKhachHangSerializer(data=request.data)
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

class KhachHangDetailAPIView(BaseNhanVienAPIView):
    def get_object(self, pk):
        try: return KhachHang.objects.get(pk=pk)
        except KhachHang.DoesNotExist: raise Http404

    def patch(self, request, pk, format=None):
        khach_hang = self.get_object(pk)
        serializer = DoiMatKhauSerializer(data=request.data)
        if serializer.is_valid():
            user = khach_hang.tai_khoan
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            return Response({'success': 'Đổi mật khẩu thành công.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        khach_hang = self.get_object(pk)
        khach_hang.tai_khoan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class NapTienAPIView(BaseNhanVienAPIView):
  # quanly/api_views.py - Trong class NapTienAPIView
# ...
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            khach_hang = KhachHang.objects.get(pk=pk)
        except KhachHang.DoesNotExist:
            return Response({'error': 'Khách hàng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            so_tien = Decimal(request.data.get('so_tien', '0'))
            if so_tien <= 0:
                return Response({'error': 'Số tiền nạp phải lớn hơn 0.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        KhachHang.objects.filter(pk=pk).update(so_du=F('so_du') + so_tien)
        GiaoDichTaiChinh.objects.create(
            ca_lam_viec=ca_hien_tai,
            khach_hang=khach_hang,
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN,
            so_tien=so_tien
        )
        
        # **********************************************
        # <<< GỬI THÔNG ĐIỆP WEBSOCKET >>>
        # **********************************************
        channel_layer = get_channel_layer()
        new_summary_data = DashboardSummaryAPIView().calculate_summary() 

        async_to_sync(channel_layer.group_send)(
            "dashboard_summary",
            {
                "type": "send_summary_update",
                "data": new_summary_data,
            },
        )
        # **********************************************

        khach_hang.refresh_from_db()
        return Response(KhachHangSerializer(khach_hang).data)
class LichSuCaAPIView(BaseNhanVienAPIView, generics.ListAPIView):
    serializer_class = CaLamViecSerializer

    def get_queryset(self):
        nhan_vien = self.get_nhan_vien(self.request)
        queryset = CaLamViec.objects.filter(
            trang_thai=CaLamViec.TrangThai.DA_KET_THUC,
            nhan_vien=nhan_vien
        ).select_related('nhan_vien__tai_khoan', 'loai_ca').order_by('-thoi_gian_ket_thuc_thuc_te')

        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')

        if start_date_str:
            queryset = queryset.filter(ngay_lam_viec__gte=start_date_str)
        if end_date_str:
            queryset = queryset.filter(ngay_lam_viec__lte=end_date_str)

        return queryset

class TongQuanDoanhThuAPIView(BaseNhanVienAPIView):
    def get(self, request, *args, **kwargs):
        nhan_vien = self.get_nhan_vien(request)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        cac_ca_cua_nv = CaLamViec.objects.filter(nhan_vien=nhan_vien, ngay_lam_viec__range=[start_date, end_date])
        
        doanh_thu_theo_ngay = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec__in=cac_ca_cua_nv,
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
            ]
        ).annotate(ngay=truncate('thoi_gian_giao_dich')).values('ngay').annotate(total=Sum('so_tien')).order_by('ngay')
        
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
            'doanh_thu_theo_ngay': list(doanh_thu_theo_ngay),
            'top_mon_an': list(top_mon_an)
        }
        return Response(data)

class ChiTietCaAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsNhanVien]
    serializer_class = ChiTietCaLamViecSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        nhan_vien = self.request.user.nhanvien
        return CaLamViec.objects.filter(trang_thai=CaLamViec.TrangThai.DA_KET_THUC, nhan_vien=nhan_vien)

class XuatBaoCaoChiTietCaAPIView(BaseNhanVienAPIView):
    def get(self, request, pk, *args, **kwargs):
        nhan_vien = self.get_nhan_vien(request)
        try:
            ca = CaLamViec.objects.get(pk=pk, nhan_vien=nhan_vien)
        except CaLamViec.DoesNotExist:
            return HttpResponse("Không tìm thấy ca làm việc hoặc bạn không có quyền truy cập.", status=404)

        serializer = ChiTietCaLamViecSerializer(ca)
        data = serializer.data
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="BaoCaoCa_{ca.id}_{ca.ngay_lam_viec.strftime("%d%m%Y")}.xlsx"'
        
        try:
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                tien_mat_dau_ca = Decimal(data.get('tien_mat_ban_dau', 0))
                tong_doanh_thu = Decimal(data.get('tong_doanh_thu_he_thong', 0))
                tien_mat_cuoi_ca = Decimal(data.get('tien_mat_cuoi_ca', 0))
                chenh_lech = Decimal(data.get('chenh_lech', 0))
                
                tong_ket_data = {
                    "Thông tin": ["Ngày", "Ca", "Nhân viên", "Thời gian", "Tiền mặt đầu ca", "Doanh thu hệ thống", "Tiền mặt cuối ca", "Chênh lệch"],
                    "Giá trị": [
                        ca.ngay_lam_viec.strftime('%d/%m/%Y'),
                        ca.loai_ca.ten_ca if ca.loai_ca else "Ca Tự Do",
                        ca.nhan_vien.tai_khoan.username,
                        f"{ca.thoi_gian_bat_dau_thuc_te.strftime('%H:%M')} - {ca.thoi_gian_ket_thuc_thuc_te.strftime('%H:%M') if ca.thoi_gian_ket_thuc_thuc_te else 'N/A'}",
                        f"{tien_mat_dau_ca:,.0f} VNĐ",
                        f"{tong_doanh_thu:,.0f} VNĐ",
                        f"{tien_mat_cuoi_ca:,.0f} VNĐ",
                        f"{chenh_lech:,.0f} VNĐ"
                    ]
                }
                pd.DataFrame(tong_ket_data).to_excel(writer, sheet_name='Tổng Kết Ca', index=False)
                
                doanh_thu_loai_data = {
                    "Loại Doanh Thu": ["Tiền giờ", "Tiền dịch vụ"],
                    "Tổng Tiền (VNĐ)": [
                        Decimal(data.get('tong_tien_gio', 0)),
                        Decimal(data.get('tong_tien_dich_vu', 0))
                    ]
                }
                pd.DataFrame(doanh_thu_loai_data).to_excel(writer, sheet_name='Tổng Hợp Doanh Thu', index=False)
                
                chi_tiet_dv = data.get('chi_tiet_dich_vu')
                if chi_tiet_dv:
                    df_dich_vu = pd.DataFrame(chi_tiet_dv)
                    df_dich_vu.rename(columns={'mon__ten_mon': 'Tên Món', 'so_luong_ban': 'Số Lượng', 'doanh_thu': 'Doanh Thu (VNĐ)'}, inplace=True)
                    df_dich_vu.to_excel(writer, sheet_name='Doanh Thu Dịch Vụ', index=False)
        except Exception as e:
            print(f"Lỗi khi tạo file Excel: {e}")
            return HttpResponse(f"Đã có lỗi xảy ra khi tạo file báo cáo: {e}", status=500)
        
        return response
