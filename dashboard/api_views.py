# dashboard/api_views.py
from quanly.permissions import IsAdminRole 
from django.forms import DecimalField
from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db import transaction
from django.db.models import Sum, F # <<< ĐÃ THÊM 'F'
from django.utils import timezone
from datetime import datetime, timedelta
from quanly.models import CaLamViec, ChiTietDonHang, HoaDon, LoaiMay, May # Thêm import này
# <<< THÊM COALESCE VÀO ĐÂY >>>
from django.db.models.functions import Coalesce 
from decimal import Decimal

# Import các serializer đã có (ĐÃ CẬP NHẬT)
from quanly.serializers import (
    CaLamViecSerializer, ChiTietCaLamViecSerializer,
    PhienSuDungSimpleSerializer, CustomerDetailSerializer, KhuyenMaiSerializer # <<< SERIALIZER MỚI ĐÃ ĐƯỢC THÊM >>>
)
from django.db.models.functions import TruncMonth
from django.db.models.functions import ExtractHour
from django.db.models.expressions import OuterRef, Subquery
from django.db.models import Sum, F, DecimalField, OuterRef, Subquery, Prefetch # Cần thêm Prefetch


# Import models từ các app khác
from accounts.models import TaiKhoan
from quanly.models import (
    GiaoDichTaiChinh, PhienSuDung, NguyenLieu, PhieuKiemKe,
    LichSuThayDoiKho, May, NhanVien, KhachHang,
    MenuItem, DanhMucMenu, DinhLuong,
    LichSuThayDoiKho, KhuyenMai, ThongBao
)

# Import các serializer cần thiết
from quanly.serializers import (
    UserAdminSerializer, PhieuKiemKeAdminSerializer, DoiMatKhauSerializer,
    NguyenLieuSerializer,LichSuThayDoiKhoSerializer, ThongBaoSerializer # <<< ĐÃ THÊM 'NguyenLieuSerializer'
)

# -----------------------------------------------------------------------------
# SERIALIZERS DÙNG RIÊNG CHO DASHBOARD API
# -----------------------------------------------------------------------------

class DanhMucMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = DanhMucMenu
        fields = ['id', 'ten_danh_muc']

class DinhLuongSerializer(serializers.ModelSerializer):
    nguyen_lieu_ten = serializers.CharField(source='nguyen_lieu.ten_nguyen_lieu', read_only=True)
    nguyen_lieu_don_vi = serializers.CharField(source='nguyen_lieu.don_vi_tinh', read_only=True)

    class Meta:
        model = DinhLuong
        fields = ['id', 'nguyen_lieu', 'nguyen_lieu_ten', 'nguyen_lieu_don_vi', 'so_luong_can']

class MenuItemDetailSerializer(serializers.ModelSerializer):
    danh_muc_ten = serializers.CharField(source='danh_muc.ten_danh_muc', read_only=True)
    dinh_luong = DinhLuongSerializer(many=True, required=False)

    class Meta:
        model = MenuItem
        fields = ['id', 'ten_mon', 'don_gia', 'danh_muc', 'danh_muc_ten', 'is_available', 'dinh_luong']

    @transaction.atomic
    def create(self, validated_data):
        dinh_luong_data = validated_data.pop('dinh_luong', [])
        menu_item = MenuItem.objects.create(**validated_data)
        for item_data in dinh_luong_data:
            DinhLuong.objects.create(menu_item=menu_item, **item_data)
        return menu_item

    @transaction.atomic
    def update(self, instance, validated_data):
        dinh_luong_data = validated_data.pop('dinh_luong', [])
        instance = super().update(instance, validated_data)
        DinhLuong.objects.filter(menu_item=instance).delete()
        for item_data in dinh_luong_data:
            DinhLuong.objects.create(menu_item=instance, **item_data)
        return instance

# -----------------------------------------------------------------------------
# API VIEWS CHO TRANG CHỦ DASHBOARD
# -----------------------------------------------------------------------------
class DashboardSummaryAPIView(APIView):
    permission_classes = [IsAdminRole]

    # <<< HÀM HELPER MỚI: Chỉ tính toán và trả về dict >>>
    def calculate_summary(self):
        # Đây là logic tính toán ĐÃ TÁCH KHỎI HÀM GET BÊN DƯỚI
        today = timezone.now().date()
        giao_dich_hom_nay = GiaoDichTaiChinh.objects.filter(thoi_gian_giao_dich__date=today)
        doanh_thu_hom_nay = giao_dich_hom_nay.filter(
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE
            ]
        ).aggregate(total=Sum('so_tien'))['total'] or 0
        so_may_dang_chay = PhienSuDung.objects.filter(trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA).count()
        tong_so_may = May.objects.count()
        canh_bao_kho = NguyenLieu.objects.filter(so_luong_ton__lte=10).order_by('so_luong_ton')[:5]
        kiem_ke_cho_xu_ly = PhieuKiemKe.objects.filter(da_xac_nhan=False).count()
        seven_days_ago = today - timedelta(days=6)
        doanh_thu_7_ngay = GiaoDichTaiChinh.objects.filter(
            thoi_gian_giao_dich__date__range=[seven_days_ago, today],
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE
            ]
        ).values('thoi_gian_giao_dich__date').annotate(total=Sum('so_tien')).order_by('thoi_gian_giao_dich__date')
        chart_labels = [(seven_days_ago + timedelta(days=i)).strftime("%d/%m") for i in range(7)]
        chart_data = [0] * 7
        for entry in doanh_thu_7_ngay:
            try:
                idx = (entry['thoi_gian_giao_dich__date'] - seven_days_ago).days
                if 0 <= idx < 7:
                    chart_data[idx] = entry['total']
            except (IndexError, TypeError):
                continue
        data = {
            'summary_today': { 'doanh_thu': doanh_thu_hom_nay, 'so_may_dang_chay': so_may_dang_chay, 'tong_so_may': tong_so_may, 'kiem_ke_cho_xu_ly': kiem_ke_cho_xu_ly, },
            'inventory_warnings': [ {'ten': nl.ten_nguyen_lieu, 'ton_kho': nl.so_luong_ton, 'don_vi': nl.don_vi_tinh} for nl in canh_bao_kho ],
            'revenue_chart': { 'labels': chart_labels, 'data': chart_data, }
        }
        return data # Trả về dict

    def get(self, request, *args, **kwargs):
        data = self.calculate_summary() # Gọi hàm helper
        return Response(data) # Trả về Response
# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ KHO (KIỂM KÊ)
# -----------------------------------------------------------------------------

class PhieuKiemKeListAPIView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        phieu_list = PhieuKiemKe.objects.prefetch_related(
            'chi_tiet__nguyen_lieu'
        ).select_related(
            'nhan_vien__tai_khoan', 'ca_lam_viec__loai_ca'
        ).order_by('da_xac_nhan', '-thoi_gian_tao')
        serializer = PhieuKiemKeAdminSerializer(phieu_list, many=True)
        return Response(serializer.data)

class XacNhanPhieuKiemKeAPIView(APIView):
    permission_classes = [IsAdminRole] 

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        # ... (Nội dung hàm này giữ nguyên, không có lỗi) ...
        try:
            phieu = PhieuKiemKe.objects.get(pk=pk, da_xac_nhan=False)
        except PhieuKiemKe.DoesNotExist:
            return Response({'error': 'Phiếu không tồn tại hoặc đã được xác nhận.'}, status=status.HTTP_404_NOT_FOUND)
        for chi_tiet in phieu.chi_tiet.all():
            nguyen_lieu = chi_tiet.nguyen_lieu
            nguyen_lieu.so_luong_ton = chi_tiet.ton_thuc_te
            nguyen_lieu.save(update_fields=['so_luong_ton'])
            if chi_tiet.chenh_lech != 0:
                LichSuThayDoiKho.objects.create( ca_lam_viec=phieu.ca_lam_viec, nhan_vien=phieu.nhan_vien, nguyen_lieu=nguyen_lieu, so_luong_thay_doi=chi_tiet.chenh_lech, loai_thay_doi=LichSuThayDoiKho.LoaiThayDoi.DIEU_CHINH, ly_do=f"Điều chỉnh sau kiểm kê cuối ca #{phieu.ca_lam_viec.id}" )
        phieu.da_xac_nhan = True
        phieu.save(update_fields=['da_xac_nhan'])
        return Response({'success': f'Đã xác nhận phiếu #{phieu.id} và cập nhật kho thành công.'})

# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ NGƯỜI DÙNG
# -----------------------------------------------------------------------------

class UserListAPIView(generics.ListAPIView):
    # ... (Nội dung class này giữ nguyên, không có lỗi) ...
    permission_classes = [IsAdminRole]
    serializer_class = UserAdminSerializer
    queryset = TaiKhoan.objects.prefetch_related('nhanvien', 'khachhang').all().order_by('username')

class UserActionAPIView(APIView):
    # ... (Nội dung class này giữ nguyên, không có lỗi) ...
    permission_classes = [IsAdminRole]
    def get_user(self, pk):
        try: return TaiKhoan.objects.get(pk=pk)
        except TaiKhoan.DoesNotExist: return None
    def patch(self, request, pk, *args, **kwargs):
        user = self.get_user(pk)
        if not user: return Response({'error': 'Người dùng không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)
        is_active = request.data.get('is_active')
        if is_active is not None and isinstance(is_active, bool):
            user.is_active = is_active
            user.save(update_fields=['is_active'])
            return Response(UserAdminSerializer(user).data)
        new_password = request.data.get('new_password')
        if new_password:
            serializer = DoiMatKhauSerializer(data={'new_password': new_password})
            if serializer.is_valid():
                user.set_password(serializer.validated_data['new_password'])
                user.save(update_fields=['password'])
                return Response({'success': f'Đã đổi mật khẩu cho {user.username}.'})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Hành động không được hỗ trợ hoặc thiếu dữ liệu.'}, status=status.HTTP_400_BAD_REQUEST)

# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ MENU
# -----------------------------------------------------------------------------

class DanhMucMenuListAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminRole] 
    serializer_class = DanhMucMenuSerializer
    queryset = DanhMucMenu.objects.all().order_by('ten_danh_muc')

class DanhMucMenuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = DanhMucMenuSerializer
    queryset = DanhMucMenu.objects.all()

class MenuItemListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = MenuItemDetailSerializer
    def get_queryset(self):
        return MenuItem.objects.select_related('danh_muc').prefetch_related('dinh_luong__nguyen_lieu').all().order_by('ten_mon')

class MenuItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = MenuItemDetailSerializer
    queryset = MenuItem.objects.select_related('danh_muc').prefetch_related('dinh_luong__nguyen_lieu').all()

# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ KHO (TỒN KHO & NHẬP HÀNG)
# -----------------------------------------------------------------------------

class NguyenLieuListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all().order_by('ten_nguyen_lieu')

class NguyenLieuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all()
# dashboard/api_views.py

class NhapKhoAPIView(APIView):
    """API chuyên dụng cho nghiệp vụ Nhập Kho."""
    permission_classes = [IsAdminRole]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        nguyen_lieu_id = request.data.get('nguyen_lieu_id')
        so_luong_nhap_str = request.data.get('so_luong_nhap')
        ly_do = request.data.get('ly_do') or "Nhập hàng từ nhà cung cấp"

        if not nguyen_lieu_id or not so_luong_nhap_str:
            return Response({'error': 'Vui lòng cung cấp đủ thông tin.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            so_luong_nhap = float(so_luong_nhap_str)
            if so_luong_nhap <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({'error': 'Số lượng nhập không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            admin_user = request.user
            try:
                nhan_vien_admin = NhanVien.objects.get(tai_khoan=admin_user)
            except NhanVien.DoesNotExist:
                nhan_vien_admin = None # Gán là None nếu không có đối tượng liên kết
                # THÊM MỘT CHECK ĐỂ KHÔNG CHO THAO TÁC NẾU USER KHÔNG PHẢI LÀ SUPERUSER
                if not admin_user.is_superuser:
                    return Response({'error': 'Tài khoản của bạn chưa được liên kết với một đối tượng Nhân viên. Vui lòng liên kết trong trang Django Admin.'}, status=status.HTTP_403_FORBIDDEN)
            # <<< END LOGIC ĐÃ SỬA >>>
            nguyen_lieu = NguyenLieu.objects.get(pk=nguyen_lieu_id)

            NguyenLieu.objects.filter(pk=nguyen_lieu_id).update(so_luong_ton=F('so_luong_ton') + so_luong_nhap)

            # <<< PHẦN SỬA LỖI NẰM Ở ĐÂY >>>
            # Giờ đây chúng ta không cần tìm ca làm việc nữa, ca_lam_viec sẽ tự động là null
            LichSuThayDoiKho.objects.create(
                ca_lam_viec=None, # Hoặc có thể bỏ trống trường này
                nhan_vien=nhan_vien_admin, 
                nguyen_lieu=nguyen_lieu,
                so_luong_thay_doi=so_luong_nhap,
                loai_thay_doi=LichSuThayDoiKho.LoaiThayDoi.NHAP_KHO,
                ly_do=ly_do
            )
            
            nguyen_lieu.refresh_from_db()
            return Response(NguyenLieuSerializer(nguyen_lieu).data, status=status.HTTP_200_OK)

        except NhanVien.DoesNotExist:
            return Response({'error': 'Tài khoản admin của bạn chưa được liên kết với một đối tượng Nhân viên. Vui lòng liên kết trong trang Django Admin.'}, status=status.HTTP_403_FORBIDDEN)
        except NguyenLieu.DoesNotExist:
            return Response({'error': 'Nguyên liệu không tồn tại.'}, status=status.HTTP_404_NOT_FOUND)
        
        

# -----------------------------------------------------------------------------
# SERIALIZERS MỚI CHO QUẢN LÝ MÁY
# -----------------------------------------------------------------------------

class LoaiMayDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiMay
        fields = ['id', 'ten_loai', 'don_gia_gio']

class MayDashboardSerializer(serializers.ModelSerializer):
    # Dùng StringRelatedField để hiển thị tên thay vì ID
    loai_may_ten = serializers.CharField(source='loai_may.ten_loai', read_only=True)

    class Meta:
        model = May
        # 'loai_may' dùng để gửi dữ liệu đi (ID), 'loai_may_ten' dùng để đọc
        fields = ['id', 'ten_may', 'trang_thai', 'loai_may', 'loai_may_ten']


# ... các API View hiện có ...

# -----------------------------------------------------------------------------
# API VIEWS MỚI CHO QUẢN LÝ MÁY
# -----------------------------------------------------------------------------

class LoaiMayListCreateAPIView(generics.ListCreateAPIView):
    """API để lấy và tạo Loại Máy."""
    permission_classes = [IsAdminRole]
    serializer_class = LoaiMayDashboardSerializer
    queryset = LoaiMay.objects.all().order_by('ten_loai')

class LoaiMayDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API để xem, sửa, xóa một Loại Máy."""
    permission_classes = [IsAdminRole, IsAdminRole]
    serializer_class = LoaiMayDashboardSerializer
    queryset = LoaiMay.objects.all()

class MayListCreateAPIView(generics.ListCreateAPIView):
    """API để lấy và tạo Máy."""
    permission_classes = [IsAdminRole]
    serializer_class = MayDashboardSerializer
    queryset = May.objects.select_related('loai_may').all().order_by('ten_may')

class MayDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API để xem, sửa, xóa một Máy."""
    permission_classes = [IsAdminRole, IsAdminRole] 
    serializer_class = MayDashboardSerializer
    queryset = May.objects.all()
    
# -----------------------------------------------------------------------------
# API VIEWS MỚI CHO BÁO CÁO
# -----------------------------------------------------------------------------

# dashboard/api_views.py

class ReportSummaryAPIView(APIView):
    """
    API cung cấp dữ liệu tóm tắt cho trang báo cáo, có thể lọc theo ngày.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({'error': 'Vui lòng cung cấp start_date và end_date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Chuyển đổi chuỗi ngày tháng sang đối tượng date
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # <<< BẮT ĐẦU PHẦN SỬA LỖI QUAN TRỌNG >>>
        # Tạo đối tượng datetime hoàn chỉnh cho việc truy vấn
        # Bắt đầu từ 00:00:00 của ngày bắt đầu
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        # Kết thúc vào 23:59:59 của ngày kết thúc
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # Queryset cơ sở sử dụng datetime
        giao_dichs = GiaoDichTaiChinh.objects.filter(thoi_gian_giao_dich__range=[start_datetime, end_datetime])
        hoa_dons = HoaDon.objects.filter(thoi_gian_tao__range=[start_datetime, end_datetime], da_thanh_toan=True)
        # <<< KẾT THÚC PHẦN SỬA LỖI QUAN TRỌNG >>>
        
        # 1. Tổng doanh thu
        tong_doanh_thu = giao_dichs.filter(
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
            ]
        ).aggregate(total=Sum('so_tien'))['total'] or 0
        
        # 2. Tổng số hóa đơn
        tong_hoa_don = hoa_dons.count()
        
        # 3. Doanh thu trung bình / hóa đơn
        doanh_thu_tb = tong_doanh_thu / tong_hoa_don if tong_hoa_don > 0 else 0
        
        # 4. Doanh thu theo từng loại
        # Lấy tổng tiền giờ từ các hóa đơn đã được lọc chính xác
        doanh_thu_gio = hoa_dons.aggregate(total=Sum('tong_tien_gio'))['total'] or 0
        
        # Lấy tổng tiền dịch vụ từ các hóa đơn đã được lọc chính xác
        doanh_thu_dich_vu_hd = hoa_dons.aggregate(total=Sum('tong_tien_dich_vu'))['total'] or 0
        # Lấy tổng tiền dịch vụ từ các đơn hàng lẻ (không có tiền giờ)
        doanh_thu_dich_vu_le = giao_dichs.filter(loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE).aggregate(total=Sum('so_tien'))['total'] or 0
        doanh_thu_dich_vu = doanh_thu_dich_vu_hd + doanh_thu_dich_vu_le
        
        data = {
            'tong_doanh_thu': tong_doanh_thu,
            'tong_hoa_don': tong_hoa_don,
            'doanh_thu_trung_binh_hoa_don': doanh_thu_tb,
            'doanh_thu_theo_loai': {
                'tien_gio': doanh_thu_gio,
                'tien_dich_vu': doanh_thu_dich_vu,
            }
        }
        return Response(data)
class CaLamViecListAPIView(generics.ListAPIView):
    """API để lấy danh sách các ca làm việc đã kết thúc, có thể lọc theo ngày."""
    permission_classes = [IsAdminRole]
    serializer_class = CaLamViecSerializer # Dùng lại serializer đã có

    def get_queryset(self):
        queryset = CaLamViec.objects.filter(trang_thai=CaLamViec.TrangThai.DA_KET_THUC).select_related('nhan_vien__tai_khoan', 'loai_ca').order_by('-thoi_gian_ket_thuc_thuc_te')
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(ngay_lam_viec__gte=start_date)
        if end_date:
            queryset = queryset.filter(ngay_lam_viec__lte=end_date)
            
        return queryset

class CaLamViecDetailAPIView(generics.RetrieveAPIView):
    """API để lấy chi tiết một ca làm việc."""
    permission_classes = [IsAdminRole]
    serializer_class = ChiTietCaLamViecSerializer # Dùng serializer chi tiết
    queryset = CaLamViec.objects.all()
    
    # -----------------------------------------------------------------------------
# API VIEWS MỚI CHO BÁO CÁO (PHÂN TÍCH HIỆU SUẤT)
# -----------------------------------------------------------------------------
# dashboard/api_views.py
# dashboard/api_views.py

# ... (các import và các class khác giữ nguyên)

# -----------------------------------------------------------------------------
# API VIEWS CHO BÁO CÁO
# -----------------------------------------------------------------------------

class ReportSummaryAPIView(APIView):
    """
    API cung cấp dữ liệu tóm tắt cho trang báo cáo, có thể lọc theo ngày.
    Đã nâng cấp để tính toán lợi nhuận.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({'error': 'Vui lòng cung cấp start_date và end_date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # Queryset cơ sở
        giao_dichs = GiaoDichTaiChinh.objects.filter(thoi_gian_giao_dich__range=[start_datetime, end_datetime])
        hoa_dons = HoaDon.objects.filter(thoi_gian_tao__range=[start_datetime, end_datetime], da_thanh_toan=True)
        
        # 1. TÍNH TOÁN DOANH THU
        tong_doanh_thu = giao_dichs.filter(
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
            ]
        ).aggregate(total=Sum('so_tien'))['total'] or 0
        
        # 2. TÍNH TOÁN GIÁ VỐN
        chi_tiet_ban_hang = ChiTietDonHang.objects.filter(
            don_hang__ca_lam_viec__cac_giao_dich__thoi_gian_giao_dich__range=[start_datetime, end_datetime]
        )
        tong_gia_von = 0
        # Dùng select_related và prefetch_related để tối ưu truy vấn
        for chi_tiet in chi_tiet_ban_hang.select_related('mon').prefetch_related('mon__dinh_luong__nguyen_lieu'):
            gia_von_mon = 0
            for dinh_luong in chi_tiet.mon.dinh_luong.all():
                # Chuyển đổi an toàn sang float
                gia_von_mon += float(dinh_luong.so_luong_can) * float(dinh_luong.nguyen_lieu.gia_von)
            
            tong_gia_von += gia_von_mon * chi_tiet.so_luong

        # 3. CÁC CHỈ SỐ KHÁC
        tong_hoa_don = hoa_dons.count()
        doanh_thu_tb = tong_doanh_thu / tong_hoa_don if tong_hoa_don > 0 else 0
        doanh_thu_gio = hoa_dons.aggregate(total=Sum('tong_tien_gio'))['total'] or 0
        doanh_thu_dich_vu_hd = hoa_dons.aggregate(total=Sum('tong_tien_dich_vu'))['total'] or 0
        doanh_thu_dich_vu_le = giao_dichs.filter(loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE).aggregate(total=Sum('so_tien'))['total'] or 0
        doanh_thu_dich_vu = doanh_thu_dich_vu_hd + doanh_thu_dich_vu_le
        
        # 4. TỔNG HỢP KẾT QUẢ
        data = {
            'tong_doanh_thu': tong_doanh_thu,
            'tong_hoa_don': tong_hoa_don,
            'doanh_thu_trung_binh_hoa_don': doanh_thu_tb,
            'doanh_thu_theo_loai': {
                'tien_gio': doanh_thu_gio,
                'tien_dich_vu': doanh_thu_dich_vu,
            },
            'tong_gia_von': tong_gia_von,
            'loi_nhuan_gop': float(tong_doanh_thu) - tong_gia_von
        }
        return Response(data)

class ProductPerformanceAPIView(APIView):
    """
    API phân tích hiệu suất sản phẩm, đã nâng cấp để tính lợi nhuận.
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({'error': 'Vui lòng cung cấp start_date và end_date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # Bước 1: Tổng hợp doanh thu và số lượng bán từ DB
        product_performance_raw = ChiTietDonHang.objects.filter(
            don_hang__ca_lam_viec__cac_giao_dich__thoi_gian_giao_dich__range=[start_datetime, end_datetime]
        ).values(
            'mon_id', 'mon__ten_mon'
        ).annotate(
            tong_so_luong_ban=Sum('so_luong'),
            tong_doanh_thu=Sum('thanh_tien')
        ).order_by('-tong_doanh_thu')

        # Bước 2: Lấy tất cả các món ăn và định lượng liên quan trong một truy vấn
        menu_items_with_dinh_luong = MenuItem.objects.filter(
            id__in=[item['mon_id'] for item in product_performance_raw]
        ).prefetch_related('dinh_luong__nguyen_lieu')

        # Tạo một dictionary để tra cứu giá vốn nhanh
        gia_von_lookup = {}
        for mon in menu_items_with_dinh_luong:
            gia_von_mon = 0
            for dl in mon.dinh_luong.all():
                gia_von_mon += float(dl.so_luong_can) * float(dl.nguyen_lieu.gia_von)
            gia_von_lookup[mon.id] = gia_von_mon

        # Bước 3: Tính toán lợi nhuận bằng Python
        final_report = []
        for item in product_performance_raw:
            gia_von_don_vi = gia_von_lookup.get(item['mon_id'], 0)
            tong_gia_von_item = gia_von_don_vi * float(item['tong_so_luong_ban'])
            
            final_report.append({
                'mon__ten_mon': item['mon__ten_mon'],
                'tong_so_luong_ban': item['tong_so_luong_ban'],
                'tong_doanh_thu': item['tong_doanh_thu'],
                'tong_gia_von': tong_gia_von_item,
                'loi_nhuan': float(item['tong_doanh_thu']) - tong_gia_von_item
            })
            
        # Sắp xếp lại theo lợi nhuận và lấy top 10
        final_report.sort(key=lambda x: x['loi_nhuan'], reverse=True)

        return Response(final_report[:10])

class PeakHoursAPIView(APIView):
    """
    API phân tích doanh thu theo từng giờ trong ngày (giờ cao điểm).
    """
    permission_classes = [IsAdminRole]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response({'error': 'Vui lòng cung cấp start_date và end_date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

        # Lấy tất cả các giao dịch trong khoảng thời gian
        giao_dichs = GiaoDichTaiChinh.objects.filter(
            thoi_gian_giao_dich__range=[start_datetime, end_datetime],
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
            ]
        ).values('thoi_gian_giao_dich', 'so_tien')

        # Xử lý dữ liệu bằng Python
        report_data = [0] * 24
        for entry in giao_dichs:
            local_time = timezone.localtime(entry['thoi_gian_giao_dich'])
            hour_index = local_time.hour
            if 0 <= hour_index < 24:
                report_data[hour_index] += entry['so_tien']
        
        report_data = [float(val) for val in report_data]

        return Response(report_data)
    
    # <<< THÊM SERIALIZER MỚI NÀY VÀO KHU VỰC SERIALIZER >>>
class CustomerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer để hiển thị dữ liệu phân tích khách hàng."""
    username = serializers.CharField(source='tai_khoan.username', read_only=True)
    
    # Khai báo các trường được tính toán từ annotate
    tong_nap_tien = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    tong_chi_tieu = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = KhachHang
        fields = ['tai_khoan_id', 'username', 'so_du', 'tong_nap_tien', 'tong_chi_tieu']
class CustomerAnalyticsAPIView(generics.ListAPIView):
    """
    API cung cấp dữ liệu phân tích khách hàng, bao gồm tổng nạp và tổng chi tiêu.
    """
    permission_classes = [IsAdminRole]
    serializer_class = CustomerAnalyticsSerializer

    def get_queryset(self):
        # Tạo subquery để tính tổng tiền nạp cho mỗi khách hàng
        tong_nap_subquery = GiaoDichTaiChinh.objects.filter(
            khach_hang=OuterRef('pk'),
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN
        ).values('khach_hang').annotate(total=Sum('so_tien')).values('total')

        # Tạo subquery để tính tổng tiền chi tiêu (thanh toán qua tài khoản)
        tong_chi_tieu_subquery = GiaoDichTaiChinh.objects.filter(
            khach_hang=OuterRef('pk'),
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
        ).values('khach_hang').annotate(total=Sum('so_tien')).values('total')
        
        # Annotate queryset chính với các giá trị từ subquery
        queryset = KhachHang.objects.select_related('tai_khoan').annotate(
            tong_nap_tien=Subquery(tong_nap_subquery, output_field=DecimalField()),
            tong_chi_tieu=Subquery(tong_chi_tieu_subquery, output_field=DecimalField())
        ).order_by('-tong_chi_tieu') # Sắp xếp theo khách hàng chi tiêu nhiều nhất

        return queryset

# -----------------------------------------------------------------------------
# API VIEWS MỚI CHO PHÂN TÍCH KHÁCH HÀNG (CRM)
# -----------------------------------------------------------------------------
# <<< CLASS NÀY ĐÃ ĐƯỢC CHÈN VÀO VỊ TRÍ ĐÚNG >>>
class CustomerDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = CustomerDetailSerializer
    lookup_field = 'pk' # pk là TaiKhoan.id

    def get_queryset(self):
        # 1. Tính toán Tổng Nạp và Tổng Chi Tiêu (giống Analytics View)
        tong_nap_subquery = GiaoDichTaiChinh.objects.filter(
            khach_hang=OuterRef('pk'),
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN
        ).values('khach_hang').annotate(total=Sum('so_tien')).values('total')

        tong_chi_tieu_subquery = GiaoDichTaiChinh.objects.filter(
            khach_hang=OuterRef('pk'),
            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK
        ).values('khach_hang').annotate(total=Sum('so_tien')).values('total')
        
        # 2. Prefetch các phiên gần đây (Top 10)
        # Prefetch sẽ được gọi tự động khi truy vấn đối tượng chính
        
        # 3. Kết hợp Annotate và Prefetch
        queryset = KhachHang.objects.select_related('tai_khoan').annotate(
            tong_nap_tien=Coalesce(Subquery(tong_nap_subquery, output_field=DecimalField()), Decimal(0)),
            tong_chi_tieu=Coalesce(Subquery(tong_chi_tieu_subquery, output_field=DecimalField()), Decimal(0)),
        ).prefetch_related(
            # <<< DÒNG ĐÃ SỬA: Thay 'cac_phien_su_dung' bằng 'phiensudung_set' >>>
            Prefetch(
                'phiensudung_set', # Tên quan hệ ngược mặc định nếu không đặt related_name
                queryset=PhienSuDung.objects.select_related('may').order_by('-thoi_gian_bat_dau')[:10],
                to_attr='lich_su_phien'
            )
        )
        
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # 4. Tính toán Top Sản Phẩm yêu thích (Top 5)
        top_mon_an = ChiTietDonHang.objects.filter(
            don_hang__phien_su_dung__khach_hang=instance # Chỉ lấy đơn hàng từ phiên của KH
        ).values('mon__ten_mon').annotate(
            so_luong_da_mua=Sum('so_luong')
        ).order_by('-so_luong_da_mua')[:5]
        
        # Gán kết quả vào instance để Serializer có thể sử dụng
        instance.top_mon_an = list(top_mon_an)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    
class LichSuKhoAPIView(generics.ListAPIView):
    """
    API cung cấp lịch sử thay đổi kho, hỗ trợ lọc theo ngày, loại thay đổi, và nhân viên.
    """
    permission_classes = [IsAdminRole]
    serializer_class = LichSuThayDoiKhoSerializer

    def get_queryset(self):
        queryset = LichSuThayDoiKho.objects.select_related(
            'nhan_vien__tai_khoan', 'nguyen_lieu'
        ).order_by('-thoi_gian')

        # --- Lọc theo Ngày tháng ---
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                queryset = queryset.filter(thoi_gian__gte=start_datetime)
            except ValueError:
                pass # Bỏ qua nếu định dạng ngày sai

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
                queryset = queryset.filter(thoi_gian__lte=end_datetime)
            except ValueError:
                pass # Bỏ qua nếu định dạng ngày sai

        # --- Lọc theo Loại thay đổi ---
        loai_thay_doi = self.request.query_params.get('loai_thay_doi')
        if loai_thay_doi and loai_thay_doi != 'all':
            queryset = queryset.filter(loai_thay_doi=loai_thay_doi)

        # --- Lọc theo Nhân viên ---
        nhan_vien_id = self.request.query_params.get('nhan_vien_id')
        if nhan_vien_id and nhan_vien_id != 'all':
            # nhan_vien_id là TaiKhoan.id, NhanVien.tai_khoan là TaiKhoan
            queryset = queryset.filter(nhan_vien__tai_khoan_id=nhan_vien_id)

        return queryset
    
# -----------------------------------------------------------------------------
# API VIEWS MỚI CHO QUẢN LÝ KHUYẾN MÃI (Ưu tiên 1 - Chức năng 3)
# -----------------------------------------------------------------------------

class KhuyenMaiListCreateAPIView(generics.ListCreateAPIView):
    """API để lấy danh sách và tạo mới mã khuyến mãi."""
    permission_classes = [IsAdminRole, IsAdminRole]
    serializer_class = KhuyenMaiSerializer
    queryset = KhuyenMai.objects.all().order_by('-ngay_bat_dau')

class KhuyenMaiDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API để xem, sửa, xóa mã khuyến mãi."""
    permission_classes = [IsAdminRole]
    serializer_class = KhuyenMaiSerializer
    queryset = KhuyenMai.objects.all()
    
class NotificationListAPIView(generics.ListAPIView):
    """
    API để lấy danh sách các thông báo chưa đọc cho Admin.
    Hỗ trợ lọc theo da_doc và giới hạn số lượng.
    """
    permission_classes = [IsAdminRole]
    serializer_class = ThongBaoSerializer

    def get_queryset(self):
        # Thông báo chỉ dành cho người dùng hiện tại (người đang đăng nhập)
        user = self.request.user
        
        # Lấy thông báo CHƯA ĐỌC, giới hạn 100 thông báo gần nhất
        queryset = ThongBao.objects.filter(
            nguoi_nhan=user,
            da_doc=False 
        ).order_by('-thoi_gian_tao')[:100]

        return queryset

class NotificationMarkReadAPIView(APIView):
    """
    API để đánh dấu một thông báo là đã đọc hoặc đánh dấu tất cả là đã đọc.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk=None, *args, **kwargs):
        user = request.user
        
        if pk is not None:
            # Đánh dấu một thông báo cụ thể là đã đọc
            try:
                ThongBao.objects.filter(pk=pk, nguoi_nhan=user).update(da_doc=True)
                return Response({'success': f'Đã đánh dấu thông báo #{pk} là đã đọc.'})
            except Exception:
                return Response({'error': 'Thông báo không tồn tại hoặc không thuộc về bạn.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Đánh dấu TẤT CẢ thông báo chưa đọc là đã đọc
            count = ThongBao.objects.filter(nguoi_nhan=user, da_doc=False).update(da_doc=True)
            return Response({'success': f'Đã đánh dấu {count} thông báo là đã đọc.'})