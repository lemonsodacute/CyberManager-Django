# quanly/api_views.py

# --- THÊM DÒNG NÀY ---
from rest_framework import generics
from .models import May, PhienSuDung, NhanVien, HoaDon # Thêm HoaDon
from decimal import Decimal # Thêm Decimal để tính toán chính xác
from .serializers import ChiTietPhienSerializer

# Các dòng import khác
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import May, PhienSuDung, NhanVien
from .serializers import MaySerializer

class DanhSachMayAPIView(generics.ListAPIView): # Bây giờ sẽ hoạt động
    """
    API endpoint để lấy danh sách tất cả các máy và trạng thái hiện tại.
    """
    queryset = May.objects.all().order_by('ten_may')
    serializer_class = MaySerializer

class MoMayAPIView(APIView):
    def post(self, request, pk, format=None):
        try:
            may = May.objects.get(pk=pk)
            # --- LOGIC MỚI: KIỂM TRA TRẠNG THÁI ---
            if may.trang_thai != 'TRONG':
                return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Kiểm tra xem có phiên nào "lơ lửng" không
            PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').update(trang_thai='DA_HUY') # Hủy các phiên lỗi nếu có

            if not hasattr(request.user, 'nhanvien'):
                return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)

            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=request.user.nhanvien,
                hinh_thuc=PhienSuDung.HinhThuc.TRA_SAU
            )
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
            return Response({'success': f'Đã mở máy {may.ten_may}.'}, status=status.HTTP_200_OK)
        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
class ChiTietPhienAPIView(generics.RetrieveAPIView):
    """
    API để lấy thông tin chi tiết của MỘT phiên đang diễn ra.
    """
    queryset = PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA')
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk' # Tìm theo ID của phiên
class KetThucPhienAPIView(APIView):
    """
    API để kết thúc một phiên, lập hóa đơn và ghi nhận thanh toán.
    """
    def post(self, request, pk, format=None):
        try:
            phien = PhienSuDung.objects.get(pk=pk, trang_thai='DANG_DIEN_RA')
            
            # 1. Chốt thời gian và trạng thái phiên
            phien.thoi_gian_ket_thuc = timezone.now()
            phien.trang_thai = 'DA_KET_THUC'
            
            # 2. Tính tiền giờ
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
            # 3. Tính tiền dịch vụ chưa thanh toán
            don_hang_chua_thanh_toan = phien.cac_don_hang.filter(trang_thai_thanh_toan='CHUA_THANH_TOAN')
            tien_dich_vu = don_hang_chua_thanh_toan.aggregate(total=Sum('tong_tien'))['total'] or 0
            
            # 4. Tạo hóa đơn
            hoa_don = HoaDon.objects.create(
                tong_tien_gio=tien_gio,
                tong_tien_dich_vu=tien_dich_vu,
                phai_thanh_toan=tien_gio + tien_dich_vu,
                trang_thai='DA_THANH_TOAN' # Giả định thanh toán ngay
            )
            phien.hoa_don = hoa_don
            phien.save()
            
            # 5. Ghi nhận giao dịch tài chính
            GiaoDichTaiChinh.objects.create(
                nhan_vien_thuc_hien=request.user.nhanvien,
                hoa_don_lien_quan=hoa_don,
                khach_hang=phien.khach_hang,
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