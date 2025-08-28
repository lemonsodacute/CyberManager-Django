# quanly/api_views.py

from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

# --- IMPORT ĐẦY ĐỦ CÁC MODEL ---
from .models import (
    May, PhienSuDung, NhanVien, HoaDon, 
    CaLamViec, GiaoDichTaiChinh, LoaiCa
)
# --- IMPORT ĐẦY ĐỦ CÁC SERIALIZER ---
from .serializers import (
    MaySerializer, ChiTietPhienSerializer, CaLamViecSerializer, LoaiCaSerializer
)


# -----------------------------------------------------------------------------
# LỚP CHA CHO CÁC API CẦN XÁC THỰC NHÂN VIÊN
# -----------------------------------------------------------------------------
class BaseNhanVienAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    def get_nhan_vien(self, request):
        try:
            return NhanVien.objects.get(tai_khoan=request.user)
        except NhanVien.DoesNotExist:
            return None
    def get_ca_hien_tai(self, nhan_vien):
        try:
            return CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai='DANG_DIEN_RA')
        except CaLamViec.DoesNotExist:
            return None

# -----------------------------------------------------------------------------
# CÁC API CÔNG KHAI VÀ QUẢN LÝ CA
# -----------------------------------------------------------------------------

class DanhSachMayAPIView(generics.ListAPIView):
    queryset = May.objects.select_related('loai_may').all().order_by('ten_may')
    serializer_class = MaySerializer

# --- LỚP MỚI BỊ THIẾU ---
class DanhSachLoaiCaAPIView(generics.ListAPIView):
    """API để lấy danh sách các loại ca đã được Admin định nghĩa."""
    queryset = LoaiCa.objects.all()
    serializer_class = LoaiCaSerializer # Bây giờ sẽ không lỗi vì đã được import


class CaLamViecHienTaiAPIView(BaseNhanVienAPIView):
    def get(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: 
            return Response({'error': 'Tài khoản không phải nhân viên hợp lệ.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: 
            return Response({'message': 'Nhân viên chưa bắt đầu ca làm việc.'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)

class BatDauCaAPIView(BaseNhanVienAPIView):
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        if self.get_ca_hien_tai(nhan_vien): 
            return Response({'error': 'Bạn đã có một ca đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)
        
        tien_mat_str = request.data.get('tien_mat_ban_dau', '0')
        loai_ca_id = request.data.get('loai_ca_id') # Nhận loai_ca_id từ front-end

        # Kiểm tra dữ liệu đầu vào
        if not loai_ca_id:
            return Response({'error': 'Vui lòng chọn loại ca.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            loai_ca = LoaiCa.objects.get(pk=loai_ca_id)
            tien_mat_ban_dau = Decimal(tien_mat_str)
        except LoaiCa.DoesNotExist:
            return Response({'error': 'Loại ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt ban đầu không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # --- SỬA LỖI Ở ĐÂY ---
        ca_moi = CaLamViec.objects.create(
            nhan_vien=nhan_vien,
            loai_ca=loai_ca,
            tien_mat_ban_dau=tien_mat_ban_dau,
            thoi_gian_bat_dau_thuc_te=timezone.now(),
            ngay_lam_viec=timezone.now().date() # <-- Cung cấp tường minh
        )
        serializer = CaLamViecSerializer(ca_moi)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ... các API còn lại (KetThucCaAPIView, MoMayAPIView, etc.)
# ...
# quanly/api_views.py

# ... (Toàn bộ các import và các lớp API đã có ở trên giữ nguyên) ...
# ... (BaseNhanVienAPIView, DanhSachMayAPIView, CaLamViecHienTaiAPIView, BatDauCaAPIView) ...
# ... (MoMayAPIView, ChiTietPhienAPIView) ...

class MoMayAPIView(BaseNhanVienAPIView):
    """API để mở một phiên sử dụng mới cho khách vãng lai."""
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Bạn phải bắt đầu ca làm việc trước khi mở máy.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            may = May.objects.get(pk=pk)
            if may.trang_thai != 'TRONG': return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)
            if PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').exists(): return Response({'error': f'Lỗi hệ thống: Máy {may.ten_may} đã có phiên chạy.'}, status=status.HTTP_400_BAD_REQUEST)

            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=nhan_vien,
                ca_lam_viec=ca_hien_tai,
                hinh_thuc='TRA_SAU'
            )
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
            
            return Response({'success': f'Đã mở máy {may.ten_may} thành công.'}, status=status.HTTP_200_OK)
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
            
class ChiTietPhienAPIView(generics.RetrieveAPIView):
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        return PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA').prefetch_related('cac_don_hang__chi_tiet__mon')

class KetThucPhienAPIView(BaseNhanVienAPIView):
    """
    API để kết thúc một phiên, lập hóa đơn, thanh toán, và lưu lại lịch sử phiên.
    """
    @transaction.atomic # Đảm bảo tất cả các hành động đều thành công, nếu có lỗi sẽ rollback
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Không tìm thấy ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            phien = PhienSuDung.objects.select_related('may__loai_may').get(pk=pk, trang_thai='DANG_DIEN_RA')
            
            # Kiểm tra xem phiên này có thuộc ca hiện tại không (tăng cường bảo mật)
            if phien.ca_lam_viec != ca_hien_tai:
                return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN)

            phien.thoi_gian_ket_thuc = timezone.now()
            
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            
            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien,
                ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio,
                tong_tien_dich_vu=tien_dich_vu,
                tong_cong=tien_gio + tien_dich_vu,
                da_thanh_toan=True
            )
            
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai,
                hoa_don=hoa_don,
                khach_hang=phien.khach_hang,
                loai_giao_dich='THANH_TOAN_HOA_DON',
                so_tien=hoa_don.tong_cong
            )
            
            don_hang_chua_tt.update(da_thanh_toan=True)
            
            # Cập nhật trạng thái máy và phiên
            phien.may.trang_thai = 'TRONG'
            phien.may.save()

            phien.trang_thai = 'DA_KET_THUC'
            phien.save()

            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': {'id': hoa_don.id, 'tong_tien': hoa_don.tong_cong}
            }, status=status.HTTP_200_OK)
            
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được xử lý.'}, status=status.HTTP_404_NOT_FOUND)
        

# -----------------------------------------------------------------------------
# API KẾT THÚC CA
# -----------------------------------------------------------------------------

class KetThucCaAPIView(BaseNhanVienAPIView):
    """
    API để nhân viên kết thúc ca làm việc, tính toán doanh thu và chênh lệch.
    """
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: 
            return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)

        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca nào đang diễn ra để kết thúc.'}, status=status.HTTP_404_NOT_FOUND)
            
        # Kiểm tra xem có phiên nào của ca này còn đang chạy không
        if PhienSuDung.objects.filter(ca_lam_viec=ca_hien_tai, trang_thai='DANG_DIEN_RA').exists():
            return Response({'error': 'Không thể kết thúc ca. Vẫn còn máy đang hoạt động trong ca này.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Lấy số tiền mặt nhân viên nhập vào từ request
        tien_mat_cuoi_ca_str = request.data.get('tien_mat_cuoi_ca', '0')
        try:
            tien_mat_cuoi_ca_nv_nhap = Decimal(tien_mat_cuoi_ca_str)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt cuối ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # Tính tổng doanh thu tiền mặt/chuyển khoản mà hệ thống ghi nhận trong ca
        giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=ca_hien_tai,
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
        )
        tong_doanh_thu_he_thong = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total'] or Decimal('0.00')
        
        # Tiền mặt cuối ca theo lý thuyết
        tien_mat_ly_thuyet = ca_hien_tai.tien_mat_ban_dau + tong_doanh_thu_he_thong
        
        # Tính chênh lệch
        chenh_lech = tien_mat_cuoi_ca_nv_nhap - tien_mat_ly_thuyet
        
        # Cập nhật trạng thái và số liệu cho ca
        ca_hien_tai.thoi_gian_ket_thuc_thuc_te = timezone.now()
        ca_hien_tai.trang_thai = 'DA_KET_THUC'
        ca_hien_tai.tien_mat_cuoi_ca = tien_mat_cuoi_ca_nv_nhap
        ca_hien_tai.tong_doanh_thu_he_thong = tong_doanh_thu_he_thong
        ca_hien_tai.chenh_lech = chenh_lech
        ca_hien_tai.save()
        
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------------------------------------------------------
# API KẾT THÚC PHIÊN
# -----------------------------------------------------------------------------
# --- ĐÂY LÀ LỚP BỊ THIẾU ---
