# quanly/api_views.py
# quanly/api_views.py
from accounts.models import TaiKhoan
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Prefetch, F
from django.contrib.auth.models import User
from django.http import Http404

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
# --- IMPORT MODELS: Gom tất cả vào một chỗ cho gọn gàng ---
# --- IMPORT MODELS: Một khối duy nhất, đầy đủ ---
from .models import (
    May, PhienSuDung, NhanVien, HoaDon, 
    CaLamViec, GiaoDichTaiChinh, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang,
    NguyenLieu, PhieuKiemKe, ChiTietKiemKe, LichSuThayDoiKho,
    KhachHang
)

# --- IMPORT SERIALIZERS: Một khối duy nhất, đầy đủ ---
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




# -----------------------------------------------------------------------------
# LỚP CHA
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
# CÁC API VIEW
# -----------------------------------------------------------------------------

class DanhSachMayAPIView(generics.ListAPIView):
    serializer_class = MaySerializer
    def get_queryset(self):
        return May.objects.select_related('loai_may').prefetch_related(
            Prefetch(
                'cac_phien_su_dung',
                queryset=PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA').order_by('-thoi_gian_bat_dau'),
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
        if not nhan_vien: 
            return Response({'error': 'Tài khoản không phải nhân viên hợp lệ.'}, status=status.HTTP_403_FORBIDDEN)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai: 
            return Response({'message': 'Nhân viên chưa bắt đầu ca làm việc.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CaLamViecSerializer(ca_hien_tai)
        return Response(serializer.data, status=status.HTTP_200_OK)

class BatDauCaAPIView(BaseNhanVienAPIView):
    @transaction.atomic
    def post(self, request, format=None):
        nhan_vien = self.get_nhan_vien(request)
        if not nhan_vien: return Response({'error': 'Tài khoản không phải nhân viên.'}, status=status.HTTP_403_FORBIDDEN)
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
            trang_thai='DANG_DIEN_RA', ca_lam_viec__trang_thai='DA_KET_THUC'
        )
        so_luong_phien_ban_giao = phien_can_ban_giao.update(ca_lam_viec=ca_moi)
        
        serializer = CaLamViecSerializer(ca_moi)
        response_data = serializer.data
        response_data['message_ban_giao'] = f"Đã nhận bàn giao {so_luong_phien_ban_giao} máy đang chạy từ ca trước."
        return Response(response_data, status=status.HTTP_201_CREATED)

class MoMayAPIView(BaseNhanVienAPIView):
    """
    API để mở máy.
    - Nếu không có 'khach_hang_id' trong request body -> Mở cho khách vãng lai (trả sau).
    - Nếu có 'khach_hang_id' -> Mở cho thành viên (trả trước, trừ tiền từ số dư).
    """
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            may = May.objects.select_for_update().get(pk=pk)
            if may.trang_thai != 'TRONG':
                return Response({'error': f'Máy {may.ten_may} không ở trạng thái sẵn sàng.'}, status=status.HTTP_400_BAD_REQUEST)

            khach_hang_id = request.data.get('khach_hang_id', None)
            khach_hang = None
            hinh_thuc = 'TRA_SAU'

            # <<< LOGIC MỚI CHO THÀNH VIÊN >>>
            if khach_hang_id:
                try:
                    khach_hang = KhachHang.objects.get(pk=khach_hang_id)
                    hinh_thuc = 'TRA_TRUOC' # Thành viên luôn là trả trước
                    if khach_hang.so_du <= 0:
                        return Response({'error': f'Tài khoản "{khach_hang.username}" không đủ số dư để mở máy.'}, status=status.HTTP_400_BAD_REQUEST)
                except KhachHang.DoesNotExist:
                    return Response({'error': 'Không tìm thấy tài khoản khách hàng này.'}, status=status.HTTP_404_NOT_FOUND)

            # Tạo phiên sử dụng
            PhienSuDung.objects.create(
                may=may,
                nhan_vien_mo_phien=nhan_vien,
                ca_lam_viec=ca_hien_tai,
                khach_hang=khach_hang, # Sẽ là None nếu là khách vãng lai
                hinh_thuc=hinh_thuc
            )
            
            may.trang_thai = 'DANG_SU_DUNG'
            may.save()
            
            message = f"Đã mở máy {may.ten_may} cho khách vãng lai."
            if khach_hang:
                message = f"Đã mở máy {may.ten_may} cho khách hàng \"{khach_hang.username}\"."

            return Response({'success': message})

        except May.DoesNotExist:
            return Response({'error': 'Không tìm thấy máy.'}, status=status.HTTP_404_NOT_FOUND)
class ChiTietPhienAPIView(generics.RetrieveAPIView):
    serializer_class = ChiTietPhienSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        return PhienSuDung.objects.filter(trang_thai='DANG_DIEN_RA').prefetch_related('cac_don_hang__chi_tiet__mon')

class KetThucPhienAPIView(BaseNhanVienAPIView):
    """
    API để kết thúc một phiên, lập hóa đơn, và thanh toán.
    - Tự động nhận biết phiên của thành viên và trừ tiền từ số dư.
    - Ghi nhận giao dịch tiền mặt cho khách vãng lai.
    """
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            phien = PhienSuDung.objects.select_for_update().select_related(
                'may__loai_may', 'khach_hang__tai_khoan' # Tải sẵn cả khách hàng
            ).get(pk=pk, trang_thai='DANG_DIEN_RA')
            
            if phien.ca_lam_viec != ca_hien_tai:
                return Response({'error': 'Bạn không có quyền xử lý phiên này.'}, status=status.HTTP_403_FORBIDDEN)

            # 1. Tính toán tổng chi phí (logic này giữ nguyên)
            phien.thoi_gian_ket_thuc = timezone.now()
            duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
            # Làm tròn lên giây gần nhất để tránh số tiền lẻ
            duration_hours = Decimal(duration_seconds) / Decimal(3600)
            
            tien_gio = duration_hours * phien.may.loai_may.don_gia_gio
            don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
            tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
            
            tong_cong = tien_gio + tien_dich_vu

            # 2. Tạo hóa đơn (logic này giữ nguyên)
            hoa_don = HoaDon.objects.create(
                phien_su_dung=phien, ca_lam_viec=ca_hien_tai,
                tong_tien_gio=tien_gio, tong_tien_dich_vu=tien_dich_vu,
                tong_cong=tong_cong, da_thanh_toan=True # Mặc định coi là đã thanh toán
            )
            
            # <<< BẮT ĐẦU LOGIC THANH TOÁN MỚI >>>
            khach_hang = phien.khach_hang
            if khach_hang:
                # ----- TRƯỜNG HỢP 1: THANH TOÁN BẰNG TÀI KHOẢN THÀNH VIÊN -----
                
                # Kiểm tra số dư (quan trọng!)
                if khach_hang.so_du < tong_cong:
                    # Nếu không đủ tiền, rollback mọi thứ và báo lỗi
                    transaction.set_rollback(True)
                    return Response({
                        'error': f'Số dư của khách hàng "{khach_hang.username}" không đủ. '
                                 f'Cần {tong_cong:,.0f} VNĐ nhưng chỉ có {khach_hang.so_du:,.0f} VNĐ.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Trừ tiền từ số dư của khách hàng
                KhachHang.objects.filter(pk=khach_hang.pk).update(so_du=F('so_du') - tong_cong)

                # Ghi lại giao dịch thanh toán bằng tài khoản
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai,
                    hoa_don=hoa_don,
                    khach_hang=khach_hang,
                    loai_giao_dich='THANH_TOAN_TK', # <<< Loại giao dịch mới
                    so_tien=tong_cong
                )
                
            else:
                # ----- TRƯỜNG HỢP 2: THANH TOÁN TIỀN MẶT CHO KHÁCH VÃNG LAI -----
                # Logic này giống như cũ
                GiaoDichTaiChinh.objects.create(
                    ca_lam_viec=ca_hien_tai,
                    hoa_don=hoa_don,
                    loai_giao_dich='THANH_TOAN_HOA_DON', # Giao dịch tiền mặt
                    so_tien=tong_cong
                )
            # <<< KẾT THÚC LOGIC THANH TOÁN MỚI >>>
            
            # 4. Cập nhật trạng thái các đối tượng liên quan (giữ nguyên)
            don_hang_chua_tt.update(da_thanh_toan=True)
            
            phien.may.trang_thai = 'TRONG'
            phien.may.save()

            phien.trang_thai = 'DA_KET_THUC'
            phien.save()

            return Response({
                'success': 'Thanh toán thành công!',
                'hoa_don': { 'id': hoa_don.id, 'tong_tien': hoa_don.tong_cong }
            })
            
        except PhienSuDung.DoesNotExist:
            return Response({'error': 'Không tìm thấy phiên đang chạy hoặc đã được xử lý.'}, status=status.HTTP_404_NOT_FOUND)
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
    (Phiên bản đã sửa lỗi trừ kho)
    """
    @transaction.atomic
    def post(self, request, format=None):
        # 1. Xác thực và lấy dữ liệu cơ bản (giữ nguyên)
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Không có ca làm việc đang hoạt động.'}, status=status.HTTP_400_BAD_REQUEST)
        items = request.data.get('items')
        loai_don_hang = request.data.get('loai_don_hang')
        phien_id = request.data.get('phien_id')
        if not items or not isinstance(items, list) or not loai_don_hang in ['GHI_NO', 'BAN_LE']:
            return Response({'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Xử lý logic theo loại đơn hàng (giữ nguyên)
        phien_su_dung = None
        if loai_don_hang == 'GHI_NO':
            if not phien_id:
                return Response({'error': 'Cần cung cấp ID của phiên để ghi nợ.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                phien_su_dung = PhienSuDung.objects.get(pk=phien_id, trang_thai='DANG_DIEN_RA')
            except PhienSuDung.DoesNotExist:
                return Response({'error': 'Phiên sử dụng không tồn tại hoặc đã kết thúc.'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Tạo đối tượng Đơn Hàng chính (giữ nguyên)
        don_hang = DonHangDichVu.objects.create(
            ca_lam_viec=ca_hien_tai, phien_su_dung=phien_su_dung,
            loai_don_hang=loai_don_hang, da_thanh_toan=(loai_don_hang == 'BAN_LE')
        )
        
        # 4. Xử lý chi tiết đơn hàng và trừ kho (PHẦN SỬA LỖI)
        tong_tien = Decimal('0.00')
        item_ids = [item['id'] for item in items]
        
        menu_items_qs = MenuItem.objects.filter(id__in=item_ids).prefetch_related('dinh_luong__nguyen_lieu')
        menu_items = {item.id: item for item in menu_items_qs}

        chi_tiet_don_hang_list = []
        
        # <<< BẮT ĐẦU PHẦN THAY ĐỔI LOGIC TRỪ KHO >>>
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

            # Lặp qua "công thức" của món ăn để trừ kho
            for dinh_luong in mon.dinh_luong.all():
                nguyen_lieu_can_tru = dinh_luong.nguyen_lieu
                so_luong_tru = dinh_luong.so_luong_can * so_luong_ban
                
                # Cập nhật trực tiếp trên database bằng update() và F()
                # Đây là cách làm an toàn và hiệu quả nhất
                NguyenLieu.objects.filter(pk=nguyen_lieu_can_tru.pk).update(
                    so_luong_ton=F('so_luong_ton') - so_luong_tru
                )
        # <<< KẾT THÚC PHẦN THAY ĐỔI >>>

        # 5. Lưu tất cả thay đổi vào database (giữ nguyên)
        if not chi_tiet_don_hang_list:
            transaction.set_rollback(True)
            return Response({'error': 'Không có sản phẩm hợp lệ trong đơn hàng.'}, status=status.HTTP_400_BAD_REQUEST)
        
        ChiTietDonHang.objects.bulk_create(chi_tiet_don_hang_list)
        don_hang.tong_tien = tong_tien
        don_hang.save()
        
        # 6. Tạo giao dịch tài chính nếu là bán lẻ (giữ nguyên)
        if loai_don_hang == 'BAN_LE':
            GiaoDichTaiChinh.objects.create(
                ca_lam_viec=ca_hien_tai, don_hang_le=don_hang,
                loai_giao_dich='THANH_TOAN_ORDER_LE', so_tien=tong_tien,
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
        
        # <<< SỬA LỖI TẠI ĐÂY: SỬ DỤNG .update() VỚI F() >>>
        NguyenLieu.objects.filter(pk=pk).update(so_luong_ton=F('so_luong_ton') - so_luong_hong)

        LichSuThayDoiKho.objects.create(
            ca_lam_viec=ca_hien_tai, nhan_vien=nhan_vien, 
            nguyen_lieu=nguyen_lieu, so_luong_thay_doi=-so_luong_hong, 
            loai_thay_doi='HUY_HANG', ly_do=ly_do
        )
        
        nguyen_lieu.refresh_from_db() # Lấy lại giá trị mới để trả về
        return Response(NguyenLieuSerializer(nguyen_lieu).data)

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
   
# -----------------------------------------------------------------------------
# CÁC API VIEW CHO QUẢN LÝ KHÁCH HÀNG
# -----------------------------------------------------------------------------
# quanly/api_views.py

# ... (các import và các view khác giữ nguyên)

class KhachHangListCreateAPIView(BaseNhanVienAPIView):
    """
    API để lấy danh sách khách hàng (GET) và tạo khách hàng mới (POST).
    Tương thích với custom user model 'accounts.TaiKhoan'.
    """
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
            # Sử dụng manager của model tùy chỉnh để tạo user mới
            # Giả định manager của bạn có phương thức create_user
            new_user = TaiKhoan.objects.create_user(
                username=data['username'],
                password=data['password']
                # Thêm các trường bắt buộc khác nếu model TaiKhoan của bạn yêu cầu
                # ví dụ: email=f"{data['username']}@example.com"
            )
            
            # Tạo đối tượng KhachHang liên kết với User mới
            new_khach_hang = KhachHang.objects.create(tai_khoan=new_user)
        
        except (IntegrityError, ValidationError) as e:
            return Response({'error': f'Lỗi khi tạo tài khoản: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Ghi lại lỗi để debug
            print(f"Lỗi không xác định khi tạo khách hàng: {e}") 
            return Response({'error': 'Đã có lỗi xảy ra ở phía máy chủ.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_serializer = KhachHangSerializer(new_khach_hang)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class KhachHangDetailAPIView(BaseNhanVienAPIView):
    """
    API để đổi mật khẩu (PATCH) và xóa (DELETE) một khách hàng.
    """
    def get_object(self, pk):
        try:
            # pk ở đây là tai_khoan_id (user_id)
            return KhachHang.objects.select_related('tai_khoan').get(pk=pk)
        except KhachHang.DoesNotExist:
            raise Http404

    def patch(self, request, pk, format=None): # Dùng PATCH để đổi mật khẩu
        khach_hang = self.get_object(pk)
        serializer = DoiMatKhauSerializer(data=request.data)
        if serializer.is_valid():
            user = khach_hang.tai_khoan
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password']) # Chỉ cập nhật trường password cho hiệu quả
            return Response({'success': 'Đổi mật khẩu thành công.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, pk, format=None):
        khach_hang = self.get_object(pk)
        # Xóa User sẽ tự động xóa KhachHang do on_delete=CASCADE
        khach_hang.tai_khoan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NapTienAPIView(BaseNhanVienAPIView):
    """API để nạp tiền vào tài khoản khách hàng."""
    @transaction.atomic
    def post(self, request, pk, format=None):
        nhan_vien = self.get_nhan_vien(request)
        ca_hien_tai = self.get_ca_hien_tai(nhan_vien)
        if not ca_hien_tai:
            return Response({'error': 'Bạn phải bắt đầu ca làm việc.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # pk ở đây là tai_khoan_id (user_id)
            khach_hang = KhachHang.objects.get(pk=pk)
        except KhachHang.DoesNotExist:
            return Response({'error': 'Khách hàng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            so_tien = Decimal(request.data.get('so_tien', '0'))
            if so_tien <= 0:
                return Response({'error': 'Số tiền nạp phải lớn hơn 0.'}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Số tiền không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)

        # Sử dụng update() với F() để cập nhật an toàn và hiệu quả
        KhachHang.objects.filter(pk=pk).update(so_du=F('so_du') + so_tien)

        # Ghi lại giao dịch
        GiaoDichTaiChinh.objects.create(
            ca_lam_viec=ca_hien_tai,
            khach_hang=khach_hang,
            loai_giao_dich='NAP_TIEN',
            so_tien=so_tien
        )
        
        khach_hang.refresh_from_db() # Lấy lại giá trị số dư mới nhất từ DB
        return Response(KhachHangSerializer(khach_hang).data)