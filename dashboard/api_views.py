# dashboard/api_views.py

from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db import transaction
from django.db.models import Sum, F # <<< ĐÃ THÊM 'F'
from django.utils import timezone
from datetime import timedelta

# Import models từ các app khác
from accounts.models import TaiKhoan
from quanly.models import (
    GiaoDichTaiChinh, PhienSuDung, NguyenLieu, PhieuKiemKe,
    LichSuThayDoiKho, May, NhanVien, KhachHang,
    MenuItem, DanhMucMenu, DinhLuong
)

# Import các serializer cần thiết
from quanly.serializers import (
    UserAdminSerializer, PhieuKiemKeAdminSerializer, DoiMatKhauSerializer,
    NguyenLieuSerializer # <<< ĐÃ THÊM 'NguyenLieuSerializer'
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
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        # ... (Nội dung hàm này giữ nguyên, không có lỗi) ...
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
        return Response(data)

# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ KHO (KIỂM KÊ)
# -----------------------------------------------------------------------------

class PhieuKiemKeListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        phieu_list = PhieuKiemKe.objects.prefetch_related(
            'chi_tiet__nguyen_lieu'
        ).select_related(
            'nhan_vien__tai_khoan', 'ca_lam_viec__loai_ca'
        ).order_by('da_xac_nhan', '-thoi_gian_tao')
        serializer = PhieuKiemKeAdminSerializer(phieu_list, many=True)
        return Response(serializer.data)

class XacNhanPhieuKiemKeAPIView(APIView):
    permission_classes = [IsAdminUser]

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
    permission_classes = [IsAdminUser]
    serializer_class = UserAdminSerializer
    queryset = TaiKhoan.objects.prefetch_related('nhanvien', 'khachhang').all().order_by('username')

class UserActionAPIView(APIView):
    # ... (Nội dung class này giữ nguyên, không có lỗi) ...
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
    serializer_class = DanhMucMenuSerializer
    queryset = DanhMucMenu.objects.all().order_by('ten_danh_muc')

class DanhMucMenuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = DanhMucMenuSerializer
    queryset = DanhMucMenu.objects.all()

class MenuItemListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = MenuItemDetailSerializer
    def get_queryset(self):
        return MenuItem.objects.select_related('danh_muc').prefetch_related('dinh_luong__nguyen_lieu').all().order_by('ten_mon')

class MenuItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = MenuItemDetailSerializer
    queryset = MenuItem.objects.select_related('danh_muc').prefetch_related('dinh_luong__nguyen_lieu').all()

# -----------------------------------------------------------------------------
# API VIEWS CHO QUẢN LÝ KHO (TỒN KHO & NHẬP HÀNG)
# -----------------------------------------------------------------------------

class NguyenLieuListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all().order_by('ten_nguyen_lieu')

class NguyenLieuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = NguyenLieuSerializer
    queryset = NguyenLieu.objects.all()
# dashboard/api_views.py

class NhapKhoAPIView(APIView):
    """API chuyên dụng cho nghiệp vụ Nhập Kho."""
    permission_classes = [IsAdminUser]

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
            nhan_vien_admin = NhanVien.objects.get(tai_khoan=admin_user)
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