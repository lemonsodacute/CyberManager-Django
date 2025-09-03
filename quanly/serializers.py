# quanly/serializers.py

from rest_framework import serializers
<<<<<<< HEAD
from .models import May, LoaiMay, PhienSuDung, KhachHang, NhanVien # Import thêm NhanVien
from .models import MenuItem, DonHangDichVu, ChiTietDonHang
from .models import LoaiCa, CaLamViec # <-- THÊM CÁC MODELS NÀY
from django.db.models import Sum, Q  # <-- THÊM Sum và Q
from django.utils import timezone   
from .models import CaLamViec, GiaoDichTaiChinh, LoaiCa, NhanVien

# -----------------------------------------------------------------------------
# KHU VỰC CÁC SERIALIZER HIỆN CÓ CỦA BẠN (Đã sửa lại để bao gồm các thay đổi bạn cung cấp)
=======
from .models import (
    May, LoaiMay, PhienSuDung, KhachHang, CaLamViec, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang
)

# -----------------------------------------------------------------------------
# SERIALIZERS DÙNG CHUNG
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
# -----------------------------------------------------------------------------

class LoaiMaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiMay
        fields = ['ten_loai', 'don_gia_gio']

class KhachHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhachHang
        fields = ['so_du']

<<<<<<< HEAD
class NhanVienSerializer(serializers.ModelSerializer): # <-- SERIALIZER CHO NHANVIEN
    # Sử dụng SlugRelatedField để lấy username trực tiếp từ User
    tai_khoan = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    class Meta:
        model = NhanVien
        fields = ['tai_khoan', 'chuc_vu']

class PhienSuDungHienTaiSerializer(serializers.ModelSerializer):
=======
# -----------------------------------------------------------------------------
# SERIALIZERS CHO API DANH SÁCH MÁY (/api/may/)
# -----------------------------------------------------------------------------

class PhienDangChaySerializer(serializers.ModelSerializer):
    """Serializer rút gọn, chỉ lấy thông tin cần thiết cho màn hình POS."""
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
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
        if obj.trang_thai == 'DANG_SU_DUNG':
            phien = PhienSuDung.objects.select_related('khach_hang').filter(
                may=obj, trang_thai='DANG_DIEN_RA'
            ).order_by('-thoi_gian_bat_dau').first()
            if phien:
<<<<<<< HEAD
                return {
                    'id': phien.id,
                    'thoi_gian_bat_dau': phien.thoi_gian_bat_dau,
                    'hinh_thuc': phien.hinh_thuc,
                    'khach_hang': KhachHangSerializer(phien.khach_hang).data if phien.khach_hang else None
                }
        return None

=======
                return PhienDangChaySerializer(phien).data
        return None

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API CA LÀM VIỆC
# -----------------------------------------------------------------------------

class LoaiCaSerializer(serializers.ModelSerializer):
    """Serializer cho Loại Ca để hiển thị trong lựa chọn bắt đầu ca."""
    class Meta:
        model = LoaiCa
        fields = ['id', 'ten_ca']

# quanly/serializers.py

# ... (các serializer khác) ...

class CaLamViecSerializer(serializers.ModelSerializer):
    nhan_vien = serializers.StringRelatedField()
    loai_ca = LoaiCaSerializer(read_only=True)
    
    class Meta:
        model = CaLamViec
        fields = [
            'id', 
            'nhan_vien', 
            'loai_ca', 
            'thoi_gian_bat_dau_thuc_te', 
            'thoi_gian_ket_thuc_thuc_te', 
            'ngay_lam_viec',
            'trang_thai', 
            'tien_mat_ban_dau',
            'tien_mat_cuoi_ca', # <-- Thêm vào
            'tong_doanh_thu_he_thong', # <-- Thêm vào
            'chenh_lech' # <-- Thêm vào
        ]
>>>>>>> 19ff6116941a3a84e2c976ff856d8b4625700d16
class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['ten_mon']

class ChiTietDonHangSerializer(serializers.ModelSerializer):
    mon = MenuItemSerializer(read_only=True)
    class Meta:
        model = ChiTietDonHang
        fields = ['mon', 'so_luong', 'thanh_tien']

class DonHangDichVuSerializer(serializers.ModelSerializer):
    chi_tiet = ChiTietDonHangSerializer(many=True, read_only=True)
    class Meta:
        model = DonHangDichVu
        fields = ['id', 'da_thanh_toan', 'tong_tien', 'chi_tiet']

class ChiTietPhienSerializer(serializers.ModelSerializer):
    """Serializer đầy đủ thông tin cho một phiên đang chạy."""
    cac_don_hang = DonHangDichVuSerializer(many=True, read_only=True)
    loai_may = LoaiMaySerializer(source='may.loai_may', read_only=True)
    ten_may = serializers.CharField(source='may.ten_may', read_only=True)
    
    class Meta:
        model = PhienSuDung
        fields = ['id', 'ten_may', 'loai_may', 'thoi_gian_bat_dau', 'hinh_thuc', 'cac_don_hang']


# -----------------------------------------------------------------------------
# THÊM CÁC SERIALIZER MỚI CHO LOẠI CA VÀ CA LÀM VIỆC
# -----------------------------------------------------------------------------
class LoaiCaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiCa
        # --- THAY ĐỔI ---
        # Thêm các trường giờ giấc vào để API trả về
        fields = ['id', 'ten_ca', 'gio_bat_dau', 'gio_ket_thuc', 'mo_ta']
class CaLamViecSerializer(serializers.ModelSerializer):
    nhan_vien = NhanVienSerializer(read_only=True)
    loai_ca = LoaiCaSerializer(read_only=True)
    tong_thu_hien_tai = serializers.SerializerMethodField() # Đảm bảo có dòng này

    class Meta:
        model = CaLamViec
        fields = [
            'id', 'nhan_vien', 'loai_ca', 'thoi_gian_bat_dau_thuc_te',
            'thoi_gian_ket_thuc_thuc_te', 'tien_mat_ban_dau', 'tien_mat_cuoi_ca',
            'trang_thai', 'ghi_chu',
            'tong_thu_hien_tai'  # Đảm bảo có trường này
        ]

    # Đảm bảo có hàm này
    def get_tong_thu_hien_tai(self, obj):
        if obj.trang_thai != 'DANG_LAM':
            return 0

        giao_dichs = GiaoDichTaiChinh.objects.filter(
            thoi_gian_giao_dich__gte=obj.thoi_gian_bat_dau_thuc_te,
            loai_giao_dich__in=[
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_HOA_DON,
                GiaoDichTaiChinh.LoaiGiaoDich.NAP_TIEN,
                GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_ORDER_LE
            ]
        )
        tong_thu = giao_dichs.aggregate(total=Sum('so_tien'))['total'] or 0
        return tong_thu

class StartShiftSerializer(serializers.Serializer):
    """Serializer dùng để nhận dữ liệu khi bắt đầu ca làm việc."""
    loai_ca_id = serializers.IntegerField()
    tien_mat_ban_dau = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def validate_loai_ca_id(self, value):
        try:
            LoaiCa.objects.get(id=value)
        except LoaiCa.DoesNotExist:
            raise serializers.ValidationError("Loại ca không tồn tại.")
        return value

class EndShiftSerializer(serializers.Serializer):
    """Serializer dùng để nhận dữ liệu khi kết thúc ca làm việc."""
    tien_mat_cuoi_ca = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    