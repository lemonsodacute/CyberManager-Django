# quanly/serializers.py

from rest_framework import serializers
from .models import May, LoaiMay, PhienSuDung, KhachHang
from .models import MenuItem, DonHangDichVu, ChiTietDonHang

class LoaiMaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoaiMay
        fields = ['ten_loai', 'don_gia_gio']

class KhachHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhachHang
        # Chỉ cần lấy số dư là đủ cho giao diện POS
        fields = ['so_du']

class PhienSuDungHienTaiSerializer(serializers.ModelSerializer):
    # SỬA LỖI: Thêm allow_null=True để chấp nhận trường hợp khách vãng lai
    khach_hang = KhachHangSerializer(read_only=True, allow_null=True)
    class Meta:
        model = PhienSuDung
        fields = ['id', 'thoi_gian_bat_dau', 'hinh_thuc', 'khach_hang']
# quanly/serializers.py

# ... các serializer khác giữ nguyên ...

class MaySerializer(serializers.ModelSerializer):
    loai_may = LoaiMaySerializer(read_only=True)
    # Đổi tên cho rõ nghĩa hơn
    phien_dang_chay = serializers.SerializerMethodField()

    class Meta:
        model = May
        # Đổi tên trường trả về trong JSON
        fields = ['id', 'ten_may', 'trang_thai', 'loai_may', 'phien_dang_chay']
        
    def get_phien_dang_chay(self, obj): # Đổi tên hàm cho khớp
        if obj.trang_thai == 'DANG_SU_DUNG':
            phien = PhienSuDung.objects.select_related('khach_hang').filter(
                may=obj, 
                trang_thai='DANG_DIEN_RA'
            ).order_by('-thoi_gian_bat_dau').first()
            
            if phien:
                # Trả về một dictionary rút gọn thay vì dùng serializer phức tạp
                return {
                    'id': phien.id, # <-- THÊM ID CỦA PHIÊN
                    'thoi_gian_bat_dau': phien.thoi_gian_bat_dau,
                    'hinh_thuc': phien.hinh_thuc,
                    'khach_hang': KhachHangSerializer(phien.khach_hang).data if phien.khach_hang else None
                }
        return None
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
        fields = ['id', 'trang_thai_thanh_toan', 'tong_tien', 'chi_tiet']

class ChiTietPhienSerializer(serializers.ModelSerializer):
    """Serializer đầy đủ thông tin cho một phiên đang chạy."""
    cac_don_hang = DonHangDichVuSerializer(many=True, read_only=True)
    loai_may = LoaiMaySerializer(source='may.loai_may', read_only=True)
    ten_may = serializers.CharField(source='may.ten_may', read_only=True)
    
    class Meta:
        model = PhienSuDung
        fields = ['id', 'ten_may', 'loai_may', 'thoi_gian_bat_dau', 'hinh_thuc', 'cac_don_hang']