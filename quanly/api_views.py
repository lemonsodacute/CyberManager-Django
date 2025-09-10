# quanly/api_views.py

from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Sum, Prefetch # <<< THÊM Prefetch
from django.db import transaction
from django.db.models import F 

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from .models import NguyenLieu, PhieuKiemKe, ChiTietKiemKe, LichSuThayDoiKho
from .serializers import NguyenLieuSerializer, ChiTietKiemKeSerializer

from .models import (
    May, PhienSuDung, NhanVien, HoaDon, 
    CaLamViec, GiaoDichTaiChinh, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang
)
from .serializers import (
    MaySerializer, 
    ChiTietPhienSerializer, 
    CaLamViecSerializer, 
    LoaiCaSerializer,
    MenuItemSerializer
)

# -----------------------------------------------------------------------------
# LỚP CHA VÀ CÁC API VIEW KHÁC (GIỮ NGUYÊN)
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
# <<< THAY ĐỔI LỚN TẠI ĐÂY >>>
# -----------------------------------------------------------------------------

class DanhSachMayAPIView(generics.ListAPIView):
    """API để lấy danh sách tất cả các máy và trạng thái hiện tại (ĐÃ TỐI ƯU)."""
    serializer_class = MaySerializer
    # queryset = May.objects.select_related('loai_may').all().order_by('ten_may') # <<< BỎ DÒNG NÀY

    def get_queryset(self):
        """
        Ghi đè phương thức này để tối ưu truy vấn, giải quyết vấn đề N+1.
        Thay vì để serializer thực hiện 1 truy vấn cho mỗi máy, chúng ta
        chủ động gom tất cả các truy vấn đó thành 1 bằng prefetch_related.
        """
        return May.objects.select_related('loai_may').prefetch_related(
            # Tạo một Prefetch object để lấy các phiên đang chạy liên quan
            Prefetch(
                'cac_phien_su_dung', # Tên related_name từ PhienSuDung tới May
                queryset=PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA').order_by('-thoi_gian_bat_dau'),
                to_attr='phien_dang_chay_prefetched' # Lưu kết quả vào thuộc tính này
            )
        ).order_by('ten_may')

# -----------------------------------------------------------------------------
# CÁC API VIEW CÒN LẠI (GIỮ NGUYÊN CẤU TRÚC)
# -----------------------------------------------------------------------------
class DanhSachLoaiCaAPIView(generics.ListAPIView):
    queryset = LoaiCa.objects.all().order_by('gio_bat_dau')
    serializer_class = LoaiCaSerializer

class MenuAPIView(generics.ListAPIView):
    queryset = MenuItem.objects.filter(is_available=True).select_related('danh_muc').order_by('danh_muc__ten_danh_muc', 'ten_mon')
    serializer_class = MenuItemSerializer

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
    """API để nhân viên bắt đầu một ca làm việc mới và nhận bàn giao phiên cũ."""
    
    @transaction.atomic # Đảm bảo tất cả các hành động đều thành công
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        if self.get_ca_hien_tai(nhan_vien): return Response({'error': 'Bạn đã có một ca đang diễn ra.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ... (phần lấy loai_ca_id và tien_mat_ban_dau giữ nguyên)
        loai_ca_id = request.data.get('loai_ca_id')
        tien_mat_str = request.data.get('tien_mat_ban_dau', '0')
        try:
            loai_ca = LoaiCa.objects.get(pk=loai_ca_id)
            tien_mat_ban_dau = Decimal(tien_mat_str)
        except LoaiCa.DoesNotExist:
            return Response({'error': 'Loại ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt ban đầu không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo ca mới
        ca_moi = CaLamViec.objects.create(
            nhan_vien=nhan_vien,
            loai_ca=loai_ca,
            tien_mat_ban_dau=tien_mat_ban_dau,
            thoi_gian_bat_dau_thuc_te=timezone.now(),
            ngay_lam_viec=timezone.now().date()
        )

        # <<< LOGIC BÀN GIAO MỚI >>>
        # Tìm tất cả các phiên đang chạy mà thuộc về các ca đã kết thúc
        phien_can_ban_giao = PhienSuDung.objects.filter(
            trang_thai='DANG_DIEN_RA',
            ca_lam_viec__trang_thai='DA_KET_THUC'
        )
        
        # Cập nhật lại ca làm việc cho các phiên này thành ca mới
        so_luong_phien_ban_giao = phien_can_ban_giao.update(ca_lam_viec=ca_moi)
        
        # (Tùy chọn) Bạn có thể thêm một ghi chú hoặc thông báo về việc bàn giao
        # ...
        
        serializer = CaLamViecSerializer(ca_moi) # Giả sử bạn có serializer này
        response_data = serializer.data
        response_data['message_ban_giao'] = f"Đã nhận bàn giao {so_luong_phien_ban_giao} máy đang chạy từ ca trước."

        return Response(response_data, status=status.HTTP_201_CREATED)
class MoMayAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Bạn phải bắt đầu ca làm việc trước khi mở máy.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            may = May.objects.select_for_update().get(pk=pk)
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
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: return Response({'error': 'Không tìm thấy ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            phien = PhienSuDung.objects.select_for_update().select_related('may__loai_may', 'khach_hang').get(pk=pk, trang_thai='DANG_DIEN_RA')
            if phien.ca_lam_viec != ca_hien_tai: return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN)

            phien.thoi_gian_ket_thuc = timezone.now()
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
            
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            
            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien, ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio, tong_tien_dich_vu=tien_dich_vu,
                tong_cong=tien_gio + tien_dich_vu, da_thanh_toan=True
            )
            
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai, hoa_don=hoa_don, khach_hang=phien.khach_hang,
                loai_giao_dich='THANH_TOAN_HOA_DON', so_tien=hoa_don.tong_cong
            )
            
            don_hang_chua_tt.update(da_thanh_toan=True)
            phien.may.trang_thai = 'TRONG'
            phien.may.save()
            phien.trang_thai = 'DA_KET_THUC'
            phien.save()

            return Response({'success': 'Thanh toán thành công!', 'hoa_don': {'id': hoa_don.id, 'tong_tien': hoa_don.tong_cong}}, status=status.HTTP_200_OK)
            
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được người khác xử lý.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Lỗi không xác định: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# quanly/api_views.py

# ... (các import và các view khác giữ nguyên)

class KetThucCaAPIView(BaseNhanVienAPIView):
    """
    API để nhân viên kết thúc ca làm việc, tính toán doanh thu và chênh lệch.
    (Đã cập nhật để cho phép máy chạy qua đêm)
    """
    def post(self, request, format=None):
        # Bước 1: Xác thực nhân viên và ca làm việc
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: 
            return Response({'error': 'Tài khoản của bạn không phải là nhân viên hợp lệ.'}, status=status.HTTP_403_FORBIDDEN)

        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca nào đang diễn ra để kết thúc.'}, status=status.HTTP_404_NOT_FOUND)
            
        # <<< THAY ĐỔI LỚN NẰM Ở ĐÂY >>>
        # Xóa bỏ hoặc vô hiệu hóa đoạn kiểm tra này
        """
        if PhienSuDung.objects.filter(ca_lam_viec=ca_hien_tai, trang_thai='DANG_DIEN_RA').exists():
            return Response({'error': 'Không thể kết thúc ca. Vẫn còn máy đang hoạt động trong ca này.'}, status=status.HTTP_400_BAD_REQUEST)
        """
            
        # Bước 3: Lấy và xác thực dữ liệu đầu vào
        tien_mat_cuoi_ca_str = request.data.get('tien_mat_cuoi_ca', '0')
        try:
            tien_mat_cuoi_ca_nv_nhap = Decimal(tien_mat_cuoi_ca_str)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền mặt cuối ca không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # Bước 4: Thực hiện tính toán bàn giao
        # (Toàn bộ logic tính toán doanh thu giữ nguyên, không thay đổi)
        giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=ca_hien_tai,
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
        )
        tong_doanh_thu_he_thong = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total'] or Decimal('0.00')
        
        tien_mat_ly_thuyet = ca_hien_tai.tien_mat_ban_dau + tong_doanh_thu_he_thong
        chenh_lech = tien_mat_cuoi_ca_nv_nhap - tien_mat_ly_thuyet
        
        # Bước 5: Cập nhật trạng thái và số liệu cho ca làm việc
        ca_hien_tai.thoi_gian_ket_thuc_thuc_te = timezone.now()
        ca_hien_tai.trang_thai = 'DA_KET_THUC'
        ca_hien_tai.tien_mat_cuoi_ca = tien_mat_cuoi_ca_nv_nhap
        ca_hien_tai.tong_doanh_thu_he_thong = tong_doanh_thu_he_thong
        ca_hien_tai.chenh_lech = chenh_lech
        ca_hien_tai.save()
        
        # Bước 6: Trả về kết quả
        # (Không cần thay đổi)
        serializer = CaLamViecSerializer(ca_hien_tai) # Giả sử bạn có serializer này
        return Response(serializer.data, status=status.HTTP_200_OK)

# ... (các view khác giữ nguyên)
# quanly/api_views.py
from django.db.models import F # Import F expression

# ... các import và view khác ...

class TaoDonHangAPIView(BaseNhanVienAPIView):
    """
    API để tạo một đơn hàng dịch vụ mới.
    - Tự động trừ kho nguyên liệu dựa trên định lượng của món ăn.
    - Hỗ trợ cả bán lẻ (BAN_LE) và ghi nợ vào phiên (GHI_NO).
    """
    @transaction.atomic
    def post(self, request, format=None):
        # 1. Xác thực và lấy dữ liệu cơ bản
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        items = request.data.get('items') # Dạng: [{'id': 1, 'so_luong': 2}, ...]
        loai_don_hang = request.data.get('loai_don_hang') # 'GHI_NO' hoặc 'BAN_LE'
        phien_id = request.data.get('phien_id')

        if not items or not isinstance(items, list) or not loai_don_hang in ['GHI_NO', 'BAN_LE']:
            return Response({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Xử lý logic theo loại đơn hàng
        phien_su_dung = None
        if loai_don_hang == 'GHI_NO':
            if not phien_id:
                return Response({'error': 'Cần cung cấp ID của phiên để ghi nợ.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                phien_su_dung = PhienSuDung.objects.get(pk=phien_id, trang_thai='DANG_DIEN_RA')
            except PhienSuDung.DoesNotExist:
                return Response({'error': 'Phiên sử dụng không tồn tại hoặc đã kết thúc.'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Tạo đối tượng Đơn Hàng chính
        don_hang = DonHangDichVu.objects.create(
            ca_lam_viec=ca_hien_tai,
            phien_su_dung=phien_su_dung,
            loai_don_hang=loai_don_hang,
            da_thanh_toan=(loai_don_hang == 'BAN_LE')
        )
        
        # 4. Xử lý chi tiết đơn hàng và trừ kho
        tong_tien = Decimal('0.00')
        item_ids = [item['id'] for item in items]
        
        # Tối ưu truy vấn: Lấy các MenuItem và các định lượng liên quan chỉ trong 2 query
        menu_items_qs = MenuItem.objects.filter(id__in=item_ids).prefetch_related('dinh_luong__nguyen_lieu')
        menu_items = {item.id: item for item in menu_items_qs}

        chi_tiet_don_hang_list = []
        nguyen_lieu_can_update_list = []

        for item_data in items:
            mon = menu_items.get(item_data.get('id'))
            if not mon:
                # Bỏ qua nếu món không tồn tại để tránh lỗi
                continue
            
            so_luong_ban = int(item_data.get('so_luong', 0))
            if so_luong_ban <= 0:
                continue

            # Thêm chi tiết đơn hàng vào danh sách để bulk_create
            thanh_tien = mon.don_gia * so_luong_ban
            chi_tiet_don_hang_list.append(
                ChiTietDonHang(don_hang=don_hang, mon=mon, so_luong=so_luong_ban, thanh_tien=thanh_tien)
            )
            tong_tien += thanh_tien

            # Logic trừ kho tự động
            for dinh_luong in mon.dinh_luong.all():
                nguyen_lieu = dinh_luong.nguyen_lieu
                so_luong_can_tru = dinh_luong.so_luong_can * so_luong_ban
                
                # Trừ kho trực tiếp trong database để tránh xung đột dữ liệu
                # Sử dụng F() expression là cách làm an toàn và hiệu quả nhất
                nguyen_lieu.so_luong_ton = F('so_luong_ton') - so_luong_can_tru
                nguyen_lieu_can_update_list.append(nguyen_lieu)

        # 5. Lưu tất cả thay đổi vào database
        if not chi_tiet_don_hang_list:
            # Nếu sau khi duyệt không có món hợp lệ nào thì rollback
            transaction.set_rollback(True)
            return Response({'error': 'Không có sản phẩm hợp lệ trong đơn hàng.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Dùng bulk_create và bulk_update để tối ưu hiệu năng
        ChiTietDonHang.objects.bulk_create(chi_tiet_don_hang_list)
        # Chỉ cập nhật trường so_luong_ton
        NguyenLieu.objects.bulk_update(nguyen_lieu_can_update_list, ['so_luong_ton'])

        don_hang.tong_tien = tong_tien
        don_hang.save()
        
        # 6. Tạo giao dịch tài chính nếu là bán lẻ
        if loai_don_hang == 'BAN_LE':
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai,
                don_hang_le=don_hang,
                loai_giao_dich='THANH_TOAN_ORDER_LE',
                so_tien=tong_tien,
                ghi_chu=f"Thanh toán cho đơn hàng bán lẻ #{don_hang.id}"
            )

        return Response({'success': 'Tạo đơn hàng thành công!', 'don_hang_id': don_hang.id}, status=status.HTTP_201_CREATED) # -----------------------------------------------------------------------------
# CÁC API VIEW CHO QUẢN LÝ KHO (MỚI)
# -----------------------------------------------------------------------------

class DanhSachNguyenLieuAPIView(generics.ListAPIView):
    """API để lấy danh sách tất cả nguyên liệu trong kho."""
    permission_classes = [IsAuthenticated]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all().order_by('ten_nguyen_lieu')


class BaoHongNguyenLieuAPIView(BaseNhanVienAPIView):
    """API để nhân viên báo hỏng hoặc hủy một số lượng nguyên liệu."""
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nguyen_lieu = NguyenLieu.objects.get(pk=pk)
        except NguyenLieu.DoesNotExist:
            return Response({'error': 'Nguyên liệu không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            so_luong_hong = float(request.data.get('so_luong', 0))
            ly_do = request.data.get('ly_do', '')
        except (ValueError, TypeError):
            return Response({'error': 'Số lượng không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        if so_luong_hong <= 0:
            return Response({'error': 'Số lượng báo hỏng phải lớn hơn 0.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ly_do:
            return Response({'error': 'Vui lòng cung cấp lý do.'}, status=status.HTTP_400_BAD_REQUEST)

        # Trừ kho
        nguyen_lieu.so_luong_ton -= so_luong_hong
        nguyen_lieu.save()

        # Ghi lại lịch sử
        LichSuThayDoiKho.objects.create(
            ca_lam_viec=ca_hien_tai,
            nhan_vien=nhan_vien,
            nguyen_lieu=nguyen_lieu,
            so_luong_thay_doi=-so_luong_hong, # Ghi số âm
            loai_thay_doi='HUY_HANG',
            ly_do=ly_do
        )

        serializer = NguyenLieuSerializer(nguyen_lieu)
        return Response(serializer.data, status=status.HTTP_200_OK)


# quanly/api_views.py
# ...

class KiemKeCuoiCaAPIView(BaseNhanVienAPIView):
    """API để nhân viên gửi báo cáo kiểm kê cuối ca. CHỈ LƯU, KHÔNG CẬP NHẬT KHO."""
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
        
        phieu = PhieuKiemKe.objects.create(
            ca_lam_viec=ca_hien_tai,
            nhan_vien=nhan_vien,
            da_xac_nhan=False # <<< THAY ĐỔI QUAN TRỌNG: Mặc định là chưa xác nhận
        )

        nguyen_lieu_ids = [item['nguyen_lieu_id'] for item in items_data]
        danh_sach_nguyen_lieu = NguyenLieu.objects.in_bulk(nguyen_lieu_ids)

        chi_tiet_list = []
        for item_data in items_data:
            nguyen_lieu = danh_sach_nguyen_lieu.get(item_data['nguyen_lieu_id'])
            if not nguyen_lieu: continue

            chi_tiet_list.append(ChiTietKiemKe(
                phieu_kiem_ke=phieu,
                nguyen_lieu=nguyen_lieu,
                ton_he_thong=nguyen_lieu.so_luong_ton, # Ghi lại số tồn hệ thống tại thời điểm đó
                ton_thuc_te=item_data['ton_thuc_te']  # Ghi lại số nhân viên đếm
            ))
            
            # <<< BỎ HOÀN TOÀN LOGIC CẬP NHẬT KHO TẠI ĐÂY >>>
        
        ChiTietKiemKe.objects.bulk_create(chi_tiet_list)

        return Response({'success': 'Đã gửi báo cáo kiểm kê thành công. Chờ quản lý xác nhận.'}, status=status.HTTP_201_CREATED)