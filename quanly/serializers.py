# quanly/serializers.py
from accounts.models import TaiKhoan 
from rest_framework import serializers
from .models import (
    ChiTietKiemKe, May, LoaiMay, PhienSuDung, KhachHang, CaLamViec, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang, NhanVien
)
from .models import NguyenLieu
from django.db.models import Sum
from django.contrib.auth.models import User
from .models import GiaoDichTaiChinh
from rest_framework.validators import UniqueValidator

# -----------------------------------------------------------------------------
# SERIALIZERS DÙNG CHUNG / NỀN TẢNG
# -----------------------------------------------------------------------------

class NhanVienSerializer(serializers.ModelSerializer):
    tai_khoan = serializers.StringRelatedField()
    class Meta:
        model = NhanVien
        fields = ['tai_khoan']

class LoaiMaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiMay
        fields = ['ten_loai', 'don_gia_gio']

class KhachHangSerializer(serializers.ModelSerializer):
    """Serializer chi tiết cho Khách Hàng."""
    username = serializers.CharField(source='tai_khoan.username', read_only=True)
    
    class Meta:
        model = KhachHang
        fields = ['tai_khoan_id', 'username', 'so_du']

class TaoKhachHangSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        # <<< SỬA LẠI DÒNG NÀY >>>
        validators=[UniqueValidator(queryset=TaiKhoan.objects.all(), message="Tên đăng nhập này đã tồn tại.")]
    )
    password = serializers.CharField(write_only=True, min_length=1, error_messages={
        'min_length': 'Mật khẩu không được để trống.'
    })

class DoiMatKhauSerializer(serializers.Serializer):
    """Serializer để validate mật khẩu mới."""
    new_password = serializers.CharField(write_only=True)

class LoaiCaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiCa
        fields = ['id', 'ten_ca', 'gio_bat_dau', 'gio_ket_thuc']

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API DANH SÁCH MÁY (/api/may/)
# -----------------------------------------------------------------------------

class PhienDangChaySerializer(serializers.ModelSerializer):
    khach_hang = KhachHangSerializer(read_only=True, allow_null=True)
    class Meta:
        model = PhienSuDung
        fields = ['id', 'thoi_gian_bat_dau', 'hinh_thuc', 'khach_hang']

class MaySerializer(serializers.ModelSerializer):
    loai_may = LoaiMaySerializer(read_only=True)
    phien_dang_chay = serializers.SerializerMethodField()
    
    class Meta:
        model = May
        fields = ['id', 'ten_may', 'trang_thai', 'loai_may', 'phien_dang_chay']
        
    def get_phien_dang_chay(self, obj):
        # <<< THAY ĐỔI LỚN >>>
        # Thay vì truy vấn DB tại đây (gây ra N+1), chúng ta sẽ sử dụng
        # thuộc tính 'phien_dang_chay_prefetched' đã được tối ưu sẵn từ view.
        # `hasattr` dùng để kiểm tra xem thuộc tính đó có tồn tại không.
        if hasattr(obj, 'phien_dang_chay_prefetched') and obj.phien_dang_chay_prefetched:
            # `phien_dang_chay_prefetched` là một list, ta lấy phần tử đầu tiên.
            return PhienDangChaySerializer(obj.phien_dang_chay_prefetched[0]).data
        return None

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API CA LÀM VIỆC
# -----------------------------------------------------------------------------

class CaLamViecSerializer(serializers.ModelSerializer):
    nhan_vien = NhanVienSerializer(read_only=True)
    loai_ca = LoaiCaSerializer(read_only=True)
    tong_thu_hien_tai = serializers.SerializerMethodField()

    class Meta:
        model = CaLamViec
        fields = [
            'id', 'nhan_vien', 'loai_ca', 'thoi_gian_bat_dau_thuc_te',
            'thoi_gian_ket_thuc_thuc_te', 'ngay_lam_viec', 'tien_mat_ban_dau',
            'trang_thai', 'tong_thu_hien_tai',
            'tien_mat_cuoi_ca', 'tong_doanh_thu_he_thong', 'chenh_lech'
        ]

    def get_tong_thu_hien_tai(self, obj):
        if obj.trang_thai != 'DANG_DIEN_RA':
            return obj.tong_doanh_thu_he_thong

        giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=obj,
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
        )
        total = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total']
        return total or 0

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API MENU & ORDER
# -----------------------------------------------------------------------------

class MenuItemSerializer(serializers.ModelSerializer):
    danh_muc = serializers.StringRelatedField()
    class Meta:
        model = MenuItem
        fields = ['id', 'ten_mon', 'don_gia', 'danh_muc', 'is_available']

class ChiTietDonHangSerializer(serializers.ModelSerializer):
    mon = MenuItemSerializer(read_only=True)
    class Meta:
        model = ChiTietDonHang
        fields = ['mon', 'so_luong', 'thanh_tien']

class DonHangDichVuSerializer(serializers.ModelSerializer):
    chi_tiet = ChiTietDonHangSerializer(many=True, read_only=True)
    class Meta:
        model = DonHangDichVu
        fields = ['id', 'loai_don_hang', 'da_thanh_toan', 'tong_tien', 'chi_tiet']

class ChiTietPhienSerializer(serializers.ModelSerializer):
    cac_don_hang = DonHangDichVuSerializer(many=True, read_only=True)
    loai_may = LoaiMaySerializer(source='may.loai_may', read_only=True)
    ten_may = serializers.CharField(source='may.ten_may', read_only=True)
    
    class Meta:
        model = PhienSuDung
        fields = ['id', 'ten_may', 'loai_may', 'thoi_gian_bat_dau', 'hinh_thuc', 'cac_don_hang']
        
        
# -----------------------------------------------------------------------------
# SERIALIZERS CHO API QUẢN LÝ KHO (MỚI)
# -----------------------------------------------------------------------------

class NguyenLieuSerializer(serializers.ModelSerializer):
    """Serializer chi tiết cho Nguyên Liệu để quản lý kho."""
    class Meta:
        model = NguyenLieu
        fields = ['id', 'ten_nguyen_lieu', 'don_vi_tinh', 'so_luong_ton']

class ChiTietKiemKeSerializer(serializers.ModelSerializer):
    """Serializer dùng trong API tạo phiếu kiểm kê."""
    nguyen_lieu_id = serializers.IntegerField()
    ton_thuc_te = serializers.FloatField()

    class Meta:
        model = ChiTietKiemKe
        fields = ['nguyen_lieu_id', 'ton_thuc_te']