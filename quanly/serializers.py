# quanly/serializers.py

from rest_framework import serializers
from .models import (
    May, LoaiMay, PhienSuDung, KhachHang, CaLamViec, LoaiCa,
    MenuItem, DonHangDichVu, ChiTietDonHang
)

# -----------------------------------------------------------------------------
# SERIALIZERS DÙNG CHUNG
# -----------------------------------------------------------------------------

class LoaiMaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiMay
        fields = ['ten_loai', 'don_gia_gio']

class KhachHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhachHang
        fields = ['so_du']

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API DANH SÁCH MÁY (/api/may/)
# -----------------------------------------------------------------------------

class PhienDangChaySerializer(serializers.ModelSerializer):
    """Serializer rút gọn, chỉ lấy thông tin cần thiết cho màn hình POS."""
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