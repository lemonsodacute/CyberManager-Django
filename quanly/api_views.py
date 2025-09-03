# quanly/api_views.py

from rest_framework import generics
from .models import May, PhienSuDung, NhanVien, HoaDon, LoaiCa, CaLamViec, GiaoDichTaiChinh # <-- THÊM CÁC MODELS NÀY
from decimal import Decimal
from django.utils import timezone # Đảm bảo có timezone
from django.db.models import Sum # THÊM Sum để tính tổng tiền dịch vụ

# Các dòng import khác
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated # Để giới hạn chỉ nhân viên/admin
from rest_framework.authentication import SessionAuthentication, BasicAuthentication # Nếu cần
# from rest_framework_simplejwt.authentication import JWTAuthentication # Nếu dùng JWT

from .serializers import (
    MaySerializer,
    ChiTietPhienSerializer,
    LoaiCaSerializer,        # <-- THÊM CÁC SERIALIZER NÀY
    CaLamViecSerializer,
    StartShiftSerializer,
    EndShiftSerializer,
    # NhanVienSerializer, # Có thể không cần nếu đã serialize trong CaLamViecSerializer
)

# Để xử lý CSRF token cho các POST request từ frontend nếu không dùng SessionAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


# -----------------------------------------------------------------------------
# CÁC API VIEW HIỆN CÓ CỦA BẠN (đã được làm rõ thêm)
# -----------------------------------------------------------------------------

class DanhSachMayAPIView(generics.ListAPIView):
    """
    API endpoint để lấy danh sách tất cả các máy và trạng thái hiện tại.
    """
    # permission_classes = [IsAuthenticated] # Chỉ cho phép người dùng đã đăng nhập
    queryset = May.objects.all().order_by('ten_may')
    serializer_class = MaySerializer

@method_decorator(csrf_exempt, name='dispatch') # Bỏ qua CSRF cho API (chỉ dùng cho phát triển, cần bảo mật hơn trong production)
class MoMayAPIView(APIView):
    """
    API để mở một máy cho khách vãng lai, tạo một phiên sử dụng mới.
    """
    # permission_classes = [IsAuthenticated] # Chỉ cho phép người dùng đã đăng nhập
    def post(self, request, pk, format=None):
        try:
            may = May.objects.get(pk=pk)
            
            # 1. Kiểm tra trạng thái máy
            if may.trang_thai != 'TRONG':
                return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Kiểm tra nhân viên và ca làm việc
            if not hasattr(request.user, 'nhanvien'):
                return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Đảm bảo nhân viên đang trong ca làm việc
            current_shift = CaLamViec.objects.filter(nhan_vien=request.user.nhanvien, trang_thai='DANG_LAM').first()
            if not current_shift:
                return Response({'error': 'Bạn phải bắt đầu ca làm việc trước khi mở máy.'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Hủy các phiên "lơ lửng" nếu có (đảm bảo sạch dữ liệu)
            PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').update(trang_thai='DA_HUY')

            # 4. Tạo phiên sử dụng mới
            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=request.user.nhanvien,
                hinh_thuc=PhienSuDung.HinhThuc.TRA_SAU, # Mặc định là trả sau cho mở máy trực tiếp
            )
            
            # 5. Cập nhật trạng thái máy
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
            return Response({'success': f'Đã mở máy {may.ten_may}.'}, status=status.HTTP_200_OK)
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChiTietPhienAPIView(generics.RetrieveAPIView):
    """
    API để lấy thông tin chi tiết của MỘT phiên đang diễn ra.
    """
    # permission_classes = [IsAuthenticated]
    queryset = PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA')
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'

@method_decorator(csrf_exempt, name='dispatch') # Bỏ qua CSRF cho API
class KetThucPhienAPIView(APIView):
    """
    API để kết thúc một phiên, lập hóa đơn và ghi nhận thanh toán.
    """
    # permission_classes = [IsAuthenticated]
    def post(self, request, pk, format=None):
        try:
            phien = PhienSuDung.objects.get(pk=pk, trang_thai='DANG_DIEN_RA')
            
            if not hasattr(request.user, 'nhanvien'):
                return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
            
            # 1. Chốt thời gian và trạng thái phiên
            phien.thoi_gian_ket_thuc = timezone.now()
            
            # 2. Tính tiền giờ
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            # Đảm bảo không có thời gian âm
            if duration_seconds < 0:
                duration_seconds = 0
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
            # 3. Tính tiền dịch vụ chưa thanh toán
            # LƯU Ý: Đảm bảo đã import Sum từ django.db.models
            don_hang_chua_thanh_toan = phien.cac_don_hang.filter(trang_thai_thanh_toan='CHUA_THANH_TOAN')
            tien_dich_vu = don_hang_chua_thanh_toan.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            
            # 4. Tạo hóa đơn
            hoa_don = HoaDon.objects.create(
                tong_tien_gio=tien_gio,
                tong_tien_dich_vu=tien_dich_vu,
                phai_thanh_toan=tien_gio + tien_dich_vu,
                trang_thai='DA_THANH_TOAN' # Giả định thanh toán ngay
            )
            phien.hoa_don = hoa_don
            phien.trang_thai = 'DA_KET_THUC' # Cập nhật trạng thái phiên SAU KHI tạo hóa đơn
            phien.save()
            
            # 5. Ghi nhận giao dịch tài chính
            GiaoDichTaiChinh.objects.create(
                nhan_vien_thuc_hien=request.user.nhanvien,
                hoa_don_lien_quan=hoa_don,
                khach_hang=phien.khach_hang, # Có thể null nếu là khách vãng lai
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                so_tien=hoa_don.phai_thanh_toan
            )
            
            # 6. Cập nhật lại trạng thái máy
            phien.may.trang_thai = 'TRONG'
            phien.may.save()

            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': {
                    'id': hoa_don.id,
                    'tong_tien': hoa_don.phai_thanh_toan
                }
            }, status=status.HTTP_200_OK)

        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------------------------------------------------------
# THÊM CÁC API VIEW MỚI CHO LOẠI CA VÀ CA LÀM VIỆC
# -----------------------------------------------------------------------------

@method_decorator(csrf_exempt, name='dispatch')
class LoaiCaListAPIView(generics.ListAPIView):
    """
    API endpoint để lấy danh sách tất cả các loại ca làm việc.
    """
    # permission_classes = [IsAuthenticated]
    queryset = LoaiCa.objects.all().order_by('ten_ca')
    serializer_class = LoaiCaSerializer

@method_decorator(csrf_exempt, name='dispatch')
class CaHienTaiAPIView(APIView):
    """
    API để lấy thông tin ca làm việc hiện tại của nhân viên đang đăng nhập.
    Nếu không có ca nào, sẽ trả về 404.
    """
    # permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        if not hasattr(request.user, 'nhanvien'):
            return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Lấy ca làm việc đang diễn ra của nhân viên hiện tại
            ca_hien_tai = CaLamViec.objects.get(nhan_vien=request.user.nhanvien, trang_thai='DANG_LAM')
            serializer = CaLamViecSerializer(ca_hien_tai)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CaLamViec.DoesNotExist:
            return Response({'error': 'Chưa có ca làm việc nào đang diễn ra.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class BatDauCaAPIView(APIView):
    """
    API để bắt đầu một ca làm việc mới cho nhân viên đang đăng nhập.
    """
    # permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        if not hasattr(request.user, 'nhanvien'):
            return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Kiểm tra xem nhân viên đã có ca đang làm việc chưa
        if CaLamViec.objects.filter(nhan_vien=request.user.nhanvien, trang_thai='DANG_LAM').exists():
            return Response({'error': 'Bạn đã có một ca làm việc đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StartShiftSerializer(data=request.data)
        if serializer.is_valid():
            loai_ca_id = serializer.validated_data['loai_ca_id']
            tien_mat_ban_dau = serializer.validated_data['tien_mat_ban_dau']

            try:
                loai_ca = LoaiCa.objects.get(pk=loai_ca_id)
            except LoaiCa.DoesNotExist:
                return Response({'error': 'Loại ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

            ca_moi = CaLamViec.objects.create(
                nhan_vien=request.user.nhanvien,
                loai_ca=loai_ca,
                tien_mat_ban_dau=tien_mat_ban_dau,
                trang_thai='DANG_LAM'
            )
            # Trả về thông tin ca vừa tạo
            response_serializer = CaLamViecSerializer(ca_moi)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class KetThucCaAPIView(APIView):
    """
    API để kết thúc ca làm việc hiện tại của nhân viên đang đăng nhập.
    """
    # permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        if not hasattr(request.user, 'nhanvien'):
            return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            ca_hien_tai = CaLamViec.objects.get(nhan_vien=request.user.nhanvien, trang_thai='DANG_LAM')
        except CaLamViec.DoesNotExist:
            return Response({'error': 'Không có ca làm việc nào đang diễn ra để kết thúc.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = EndShiftSerializer(data=request.data)
        if serializer.is_valid():
            tien_mat_cuoi_ca = serializer.validated_data['tien_mat_cuoi_ca']
            
            ca_hien_tai.thoi_gian_ket_thuc_thuc_te = timezone.now()
            ca_hien_tai.tien_mat_cuoi_ca = tien_mat_cuoi_ca
            ca_hien_tai.trang_thai = 'DA_KET_THUC'
            ca_hien_tai.save()

            # Có thể thêm logic tính toán tổng thu trong ca và ghi vào GiaoDichTaiChinh nếu cần
            # Ví dụ: tính toán tổng tiền các hóa đơn liên quan đến ca này.
            # Sau khi kết thúc ca, người dùng thường sẽ được yêu cầu đăng xuất
            return Response({'success': 'Đã kết thúc ca làm việc thành công. Vui lòng đăng xuất.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)