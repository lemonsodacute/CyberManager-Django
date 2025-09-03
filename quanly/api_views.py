# quanly/api_views.py

<<<<<<< HEAD
from rest_framework import generics
from .models import May, PhienSuDung, NhanVien, HoaDon, LoaiCa, CaLamViec, GiaoDichTaiChinh # <-- THÊM CÁC MODELS NÀY
from decimal import Decimal
from django.utils import timezone # Đảm bảo có timezone
from django.db.models import Sum # THÊM Sum để tính tổng tiền dịch vụ
=======
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
<<<<<<< HEAD
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
=======
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
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Bạn phải bắt đầu ca làm việc trước khi mở máy.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            may = May.objects.get(pk=pk)
<<<<<<< HEAD
            
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
=======
            if may.trang_thai != 'TRONG': return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)
            if PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').exists(): return Response({'error': f'Lỗi hệ thống: Máy {may.ten_may} đã có phiên chạy.'}, status=status.HTTP_400_BAD_REQUEST)
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16

            # 3. Hủy các phiên "lơ lửng" nếu có (đảm bảo sạch dữ liệu)
            PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').update(trang_thai='DA_HUY')

            # 4. Tạo phiên sử dụng mới
            PhienSuDung.objects.create(
                may=may,
<<<<<<< HEAD
                nhan_vien_mo_phien=request.user.nhanvien,
                hinh_thuc=PhienSuDung.HinhThuc.TRA_SAU, # Mặc định là trả sau cho mở máy trực tiếp
=======
                nhan_vien_mo_phien=nhan_vien,
                ca_lam_viec=ca_hien_tai,
                hinh_thuc='TRA_SAU'
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
            )
            
            # 5. Cập nhật trạng thái máy
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
            
            return Response({'success': f'Đã mở máy {may.ten_may} thành công.'}, status=status.HTTP_200_OK)
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
<<<<<<< HEAD
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
=======
            
class ChiTietPhienAPIView(generics.RetrieveAPIView):
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        return PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA').prefetch_related('cac_don_hang__chi_tiet__mon')

class KetThucPhienAPIView(BaseNhanVienAPIView):
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
    """
    API để kết thúc một phiên, lập hóa đơn, thanh toán, và lưu lại lịch sử phiên.
    """
<<<<<<< HEAD
    # permission_classes = [IsAuthenticated]
=======
    @transaction.atomic # Đảm bảo tất cả các hành động đều thành công, nếu có lỗi sẽ rollback
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Không tìm thấy ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            phien = PhienSuDung.objects.select_related('may__loai_may').get(pk=pk, trang_thai='DANG_DIEN_RA')
            
<<<<<<< HEAD
            if not hasattr(request.user, 'nhanvien'):
                return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
            
            # 1. Chốt thời gian và trạng thái phiên
=======
            # Kiểm tra xem phiên này có thuộc ca hiện tại không (tăng cường bảo mật)
            if phien.ca_lam_viec != ca_hien_tai:
                return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN)

>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
            phien.thoi_gian_ket_thuc = timezone.now()
            
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            # Đảm bảo không có thời gian âm
            if duration_seconds < 0:
                duration_seconds = 0
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
<<<<<<< HEAD
            # 3. Tính tiền dịch vụ chưa thanh toán
            # LƯU Ý: Đảm bảo đã import Sum từ django.db.models
            don_hang_chua_thanh_toan = phien.cac_don_hang.filter(trang_thai_thanh_toan='CHUA_THANH_TOAN')
            tien_dich_vu = don_hang_chua_thanh_toan.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
=======
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
            
            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien,
                ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio,
                tong_tien_dich_vu=tien_dich_vu,
                tong_cong=tien_gio + tien_dich_vu,
                da_thanh_toan=True
            )
<<<<<<< HEAD
            phien.hoa_don = hoa_don
            phien.trang_thai = 'DA_KET_THUC' # Cập nhật trạng thái phiên SAU KHI tạo hóa đơn
            phien.save()
=======
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
            
            GiaoDichTaiChinh.objects.create(
<<<<<<< HEAD
                nhan_vien_thuc_hien=request.user.nhanvien,
                hoa_don_lien_quan=hoa_don,
                khach_hang=phien.khach_hang, # Có thể null nếu là khách vãng lai
                loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                so_tien=hoa_don.phai_thanh_toan
=======
                ca_lam_viec=ca_hien_tai,
                hoa_don=hoa_don,
                khach_hang=phien.khach_hang,
                loai_giao_dich='THANH_TOAN_HOA_DON',
                so_tien=hoa_don.tong_cong
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
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
<<<<<<< HEAD
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
=======
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
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
