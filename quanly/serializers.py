from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.db.models import Sum

# Import custom user model của bạn
from accounts.models import TaiKhoan

# Import tất cả các model cần thiết từ app 'quanly'
from .models import (
    NhanVien, KhachHang, LoaiMay, May, PhienSuDung,
    CaLamViec, LoaiCa, GiaoDichTaiChinh, HoaDon,
    MenuItem, DonHangDichVu, ChiTietDonHang,
    NguyenLieu, PhieuKiemKe, ChiTietKiemKe,
    LichSuThayDoiKho,  KhuyenMai
)

# -----------------------------------------------------------------------------
# SERIALIZERS DÙNG CHUNG / NỀN TẢNG
# -----------------------------------------------------------------------------

class UserAdminSerializer(serializers.ModelSerializer):
    """Serializer để Admin xem và quản lý tất cả người dùng."""
    loai_tai_khoan = serializers.SerializerMethodField()
    so_du = serializers.DecimalField(source='khachhang.so_du', max_digits=12, decimal_places=2, read_only=True, default=None)

    class Meta:
        model = TaiKhoan # Sử dụng custom user model của bạn
        fields = ['id', 'username', 'email', 'is_active', 'loai_tai_khoan', 'so_du']
    
    def get_loai_tai_khoan(self, obj):
        if hasattr(obj, 'nhanvien'):
            return "Nhân viên"
        if hasattr(obj, 'khachhang'):
            return "Khách hàng"
        if obj.is_superuser:
            return "Admin"
        return "Chưa phân loại"
        
class NhanVienSerializer(serializers.ModelSerializer):
    """Serializer đơn giản cho Nhân Viên, hiển thị username."""
    tai_khoan = serializers.StringRelatedField()
    class Meta:
        model = NhanVien
        fields = ['tai_khoan']

class LoaiMaySerializer(serializers.ModelSerializer):
    """Serializer cho Loại Máy."""
    class Meta:
        model = LoaiMay
        fields = ['ten_loai', 'don_gia_gio']

class KhachHangSerializer(serializers.ModelSerializer):
    """Serializer chi tiết cho Khách Hàng, hiển thị username và số dư."""
    username = serializers.CharField(source='tai_khoan.username', read_only=True)
    class Meta:
        model = KhachHang
        fields = ['tai_khoan_id', 'username', 'so_du']

class TaoKhachHangSerializer(serializers.Serializer):
    """Serializer để validate dữ liệu khi tạo khách hàng mới."""
    username = serializers.CharField(
        max_length=150,
        validators=[UniqueValidator(queryset=TaiKhoan.objects.all(), message="Tên đăng nhập này đã tồn tại.")]
    )
    password = serializers.CharField(write_only=True, min_length=1, error_messages={
        'min_length': 'Mật khẩu không được để trống.'
    })

class DoiMatKhauSerializer(serializers.Serializer):
    """Serializer để validate mật khẩu mới."""
    new_password = serializers.CharField(write_only=True)

class LoaiCaSerializer(serializers.ModelSerializer):
    """Serializer cho Loại Ca."""
    class Meta:
        model = LoaiCa
        fields = ['id', 'ten_ca', 'gio_bat_dau', 'gio_ket_thuc']

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API SƠ ĐỒ MÁY
# -----------------------------------------------------------------------------

class PhienDangChaySerializer(serializers.ModelSerializer):
    """Serializer rút gọn cho phiên đang chạy, hiển thị trên sơ đồ máy."""
    khach_hang = KhachHangSerializer(read_only=True, allow_null=True)
    class Meta:
        model = PhienSuDung
        fields = ['id', 'thoi_gian_bat_dau', 'hinh_thuc', 'khach_hang']

class MaySerializer(serializers.ModelSerializer):
    """Serializer chính cho mỗi máy trên sơ đồ."""
    loai_may = LoaiMaySerializer(read_only=True)
    phien_dang_chay = serializers.SerializerMethodField()
    
    class Meta:
        model = May
        fields = ['id', 'ten_may', 'trang_thai', 'loai_may', 'phien_dang_chay']
        
    def get_phien_dang_chay(self, obj):
        if hasattr(obj, 'phien_dang_chay_prefetched') and obj.phien_dang_chay_prefetched:
            return PhienDangChaySerializer(obj.phien_dang_chay_prefetched[0]).data
        return None

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
    """Serializer đầy đủ thông tin cho một phiên khi click vào xem chi tiết."""
    cac_don_hang = DonHangDichVuSerializer(many=True, read_only=True)
    loai_may = LoaiMaySerializer(source='may.loai_may', read_only=True)
    ten_may = serializers.CharField(source='may.ten_may', read_only=True)
    khach_hang = KhachHangSerializer(read_only=True)
    
    class Meta:
        model = PhienSuDung
        fields = ['id', 'ten_may', 'loai_may', 'khach_hang', 'thoi_gian_bat_dau', 'hinh_thuc', 'cac_don_hang']

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API QUẢN LÝ KHO
# -----------------------------------------------------------------------------

class NguyenLieuSerializer(serializers.ModelSerializer):
    """Serializer chi tiết cho Nguyên Liệu để quản lý kho."""
    class Meta:
        model = NguyenLieu
        fields = ['id', 'ten_nguyen_lieu', 'don_vi_tinh', 'so_luong_ton']

class ChiTietKiemKeSerializer(serializers.ModelSerializer):
    """Serializer dùng trong API tạo phiếu kiểm kê của nhân viên."""
    nguyen_lieu_id = serializers.IntegerField()
    ton_thuc_te = serializers.FloatField()

    class Meta:
        model = ChiTietKiemKe
        fields = ['nguyen_lieu_id', 'ton_thuc_te']

# -----------------------------------------------------------------------------
# SERIALIZERS CHO API CA LÀM VIỆC & BÁO CÁO
# -----------------------------------------------------------------------------

class CaLamViecSerializer(serializers.ModelSerializer):
    """Serializer tổng quan cho ca làm việc."""
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
        if obj.trang_thai == 'DA_KET_THUC':
            return obj.tong_doanh_thu_he_thong

        giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=obj,
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
        )
        total = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total']
        return total or 0

class ChiTietCaLamViecSerializer(serializers.ModelSerializer):
    """Serializer siêu chi tiết cho một ca làm việc, dùng cho trang báo cáo."""
    nhan_vien = serializers.CharField(source='nhan_vien.tai_khoan.username', read_only=True)
    loai_ca = serializers.CharField(source='loai_ca.ten_ca', read_only=True)
    tong_tien_gio = serializers.SerializerMethodField()
    tong_tien_dich_vu = serializers.SerializerMethodField()
    chi_tiet_dich_vu = serializers.SerializerMethodField()

    class Meta:
        model = CaLamViec
        fields = [
            'id', 'ngay_lam_viec', 'nhan_vien', 'loai_ca', 
            'thoi_gian_bat_dau_thuc_te', 'thoi_gian_ket_thuc_thuc_te',
            'tien_mat_ban_dau', 'tien_mat_cuoi_ca', 'tong_doanh_thu_he_thong', 'chenh_lech',
            'tong_tien_gio', 'tong_tien_dich_vu', 'chi_tiet_dich_vu'
        ]

    def get_tong_tien_gio(self, obj):
        return obj.cac_hoa_don.aggregate(total=Sum('tong_tien_gio'))['total'] or 0

    def get_tong_tien_dich_vu(self, obj):
        tong_dv = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=obj, 
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE']
        ).aggregate(
            total_dv_in_hoa_don=Sum('hoa_don__tong_tien_dich_vu'),
            total_dv_le=Sum('don_hang_le__tong_tien')
        )
        total_dv1 = tong_dv.get('total_dv_in_hoa_don') or 0
        total_dv2 = tong_dv.get('total_dv_le') or 0
        return total_dv1 + total_dv2

    def get_chi_tiet_dich_vu(self, obj):
        chi_tiet_items = ChiTietDonHang.objects.filter(don_hang__ca_lam_viec=obj)
        report = chi_tiet_items.values('mon__ten_mon').annotate(
            so_luong_ban=Sum('so_luong'),
            doanh_thu=Sum('thanh_tien')
        ).order_by('-doanh_thu')
        return report

# -----------------------------------------------------------------------------
# SERIALIZERS CHO ADMIN DASHBOARD
# -----------------------------------------------------------------------------
class ChiTietKiemKeAdminSerializer(serializers.ModelSerializer):
    """Serializer để hiển thị chi tiết kiểm kê trong trang Admin."""
    nguyen_lieu = serializers.CharField(source='nguyen_lieu.ten_nguyen_lieu', read_only=True)
    don_vi_tinh = serializers.CharField(source='nguyen_lieu.don_vi_tinh', read_only=True)
    
    # <<< THÊM CÁC DÒNG NÀY ĐỂ ĐẢM BẢO KIỂU DỮ LIỆU ĐÚNG >>>
    ton_he_thong = serializers.FloatField()
    ton_thuc_te = serializers.FloatField()
    chenh_lech = serializers.FloatField()

    class Meta:
        model = ChiTietKiemKe
        fields = ['nguyen_lieu', 'don_vi_tinh', 'ton_he_thong', 'ton_thuc_te', 'chenh_lech']
        
class PhieuKiemKeAdminSerializer(serializers.ModelSerializer):
    """Serializer để hiển thị danh sách phiếu kiểm kê cho Admin."""
    nhan_vien = serializers.CharField(source='nhan_vien.tai_khoan.username', read_only=True)
    ca_lam_viec_info = serializers.CharField(source='ca_lam_viec.__str__', read_only=True)
    chi_tiet = ChiTietKiemKeAdminSerializer(many=True, read_only=True)

    class Meta:
        model = PhieuKiemKe
        fields = ['id', 'ca_lam_viec_info', 'nhan_vien', 'thoi_gian_tao', 'da_xac_nhan', 'chi_tiet']
        
        
        
# -----------------------------------------------------------------------------
# SERIALIZERS MỚI CHO LỊCH SỬ KHO (DASHBOARD)
# -----------------------------------------------------------------------------
class LichSuThayDoiKhoSerializer(serializers.ModelSerializer):
    """Serializer để hiển thị chi tiết lịch sử thay đổi kho."""
    
    # Sử dụng StringRelatedField để hiển thị tên thay vì ID
    nhan_vien = serializers.CharField(source='nhan_vien.tai_khoan.username', read_only=True)
    nguyen_lieu = serializers.CharField(source='nguyen_lieu.ten_nguyen_lieu', read_only=True)
    don_vi_tinh = serializers.CharField(source='nguyen_lieu.don_vi_tinh', read_only=True)
    
    # Hiển thị tên đầy đủ của loại thay đổi (VD: Nhập kho từ nhà cung cấp)
    loai_thay_doi_display = serializers.CharField(source='get_loai_thay_doi_display', read_only=True)
    
    class Meta:
        model = LichSuThayDoiKho
        fields = [
            'thoi_gian', 'nhan_vien', 'nguyen_lieu', 'don_vi_tinh',
            'so_luong_thay_doi', 'loai_thay_doi_display', 'ly_do'
        ]

# ... (Các Serializer khác) ...

# -----------------------------------------------------------------------------
# SERIALIZERS MỚI CHO DASHBOARD CRM
# -----------------------------------------------------------------------------
# <<< VỊ TRÍ CHÍNH XÁC CỦA CÁC SERIALIZER CRM MỚI >>>
class PhienSuDungSimpleSerializer(serializers.ModelSerializer):
    """Serializer rút gọn cho Lịch sử phiên trên trang chi tiết khách hàng."""
    may_ten = serializers.CharField(source='may.ten_may', read_only=True)
    
    class Meta:
        model = PhienSuDung
        fields = ['id', 'may_ten', 'thoi_gian_bat_dau', 'thoi_gian_ket_thuc', 'trang_thai']

# quanly/serializers.py (Đảm bảo có class Meta này)

class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializer Chi tiết cho Khách Hàng (Dùng cho Dashboard)."""
    username = serializers.CharField(source='tai_khoan.username', read_only=True)
    
    # Các trường được Annotate (tính toán ở API View)
    tong_nap_tien = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    tong_chi_tieu = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    # Các trường mới được tính toán (Top món và Lịch sử phiên)
    top_mon_an = serializers.SerializerMethodField()
    # Dùng tên trường đã được Prefetch trong API View
    lich_su_phien = PhienSuDungSimpleSerializer(many=True, read_only=True) 

    class Meta: # <<< DÒNG BỊ THIẾU/MẤT LÀ ĐÂY >>>
        model = KhachHang
        fields = ['tai_khoan_id', 'username', 'so_du', 'tong_nap_tien', 'tong_chi_tieu', 'top_mon_an', 'lich_su_phien']
        
    def get_top_mon_an(self, obj):
        # Top món ăn đã được tính và gán vào obj.top_mon_an trong API View
        return obj.top_mon_an if hasattr(obj, 'top_mon_an') else []
    
    
class KhuyenMaiSerializer(serializers.ModelSerializer):
    """Serializer cho việc quản lý Khuyến mãi."""
    
    # Custom field để hiển thị loại giảm giá một cách thân thiện
    loai_giam_gia_display = serializers.CharField(source='get_loai_giam_gia_display', read_only=True)
    
    class Meta:
        model = KhuyenMai
        fields = [
            'id', 'ma_khuyen_mai', 'mo_ta', 'loai_giam_gia', 'loai_giam_gia_display', 
            'gia_tri', 'ngay_bat_dau', 'ngay_ket_thuc', 'is_active'
        ]
        read_only_fields = ['loai_giam_gia_display']
    chu_ky_lap_lai_display = serializers.CharField(source='get_chu_ky_lap_lai_display', read_only=True)
    
    class Meta:
        model = KhuyenMai
        fields = [
            'id', 'ma_khuyen_mai', 'mo_ta', 'loai_giam_gia', 'loai_giam_gia_display', 
            'gia_tri', 'ngay_bat_dau', 'ngay_ket_thuc', 'is_active',
            # <<< CÁC TRƯỜNG MỚI >>>
            'chu_ky_lap_lai', 'chu_ky_lap_lai_display', 'ngay_trong_tuan' 
        ]
        read_only_fields = ['loai_giam_gia_display', 'chu_ky_lap_lai_display']