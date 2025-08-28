# quanly/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
import decimal
from datetime import datetime

from .models import (
    May, PhienSuDung, NhanVien, CaLamViec, LoaiCa,
    HoaDon, GiaoDichTaiChinh, MenuItem, DanhMucMenu
)

# -----------------------------------------------------------------------------
# VIEW CHÍNH CHO GIAO DIỆN POS
# -----------------------------------------------------------------------------

@login_required
def pos_view(request):
    """View chính hiển thị giao diện POS với dữ liệu từ database"""
    
    # Kiểm tra xem user có phải nhân viên không
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
    except NhanVien.DoesNotExist:
        messages.error(request, 'Tài khoản của bạn không có quyền truy cập POS.')
        return redirect('admin:index')
    
    # Lấy ca làm việc hiện tại (nếu có)
    ca_hien_tai = CaLamViec.objects.filter(
        nhan_vien=nhan_vien, 
        trang_thai='DANG_DIEN_RA'
    ).first()
    
    # Lấy danh sách tất cả máy với thông tin phiên chạy
    danh_sach_may = May.objects.select_related('loai_may').prefetch_related(
        'cac_phien_su_dung'
    ).all().order_by('ten_may')
    
    # Thêm thông tin phiên đang chạy cho mỗi máy
    for may in danh_sach_may:
        phien_dang_chay = may.cac_phien_su_dung.filter(
            trang_thai='DANG_DIEN_RA'
        ).first()
        may.phien_hien_tai = phien_dang_chay
        
        # Tính thời gian chạy nếu có phiên
        if phien_dang_chay:
            thoi_gian_chay = timezone.now() - phien_dang_chay.thoi_gian_bat_dau
            may.thoi_gian_chay_phut = int(thoi_gian_chay.total_seconds() / 60)
            
            # Tính tiền giờ tạm tính
            gio_chay = thoi_gian_chay.total_seconds() / 3600
            may.tien_gio_tam_tinh = Decimal(gio_chay) * may.loai_may.don_gia_gio
    
    # Lấy danh sách loại ca để hiển thị khi bắt đầu ca
    danh_sach_loai_ca = LoaiCa.objects.all()
    
    # Tính tổng thu của ca hiện tại (nếu có)
    tong_thu_ca = Decimal('0.00')
    if ca_hien_tai:
        tong_thu_ca = GiaoDichTaiChinh.objects.filter(
            ca_lam_viec=ca_hien_tai,
            loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
        ).aggregate(total=Sum('so_tien'))['total'] or Decimal('0.00')
    
    # Thống kê máy theo trạng thái
    so_may_trong = danh_sach_may.filter(trang_thai='TRONG').count()
    so_may_dang_chay = danh_sach_may.filter(trang_thai='DANG_SU_DUNG').count()
    so_may_hong = danh_sach_may.filter(trang_thai='HONG').count()
    
    context = {
        'nhan_vien': nhan_vien,
        'ca_hien_tai': ca_hien_tai,
        'danh_sach_may': danh_sach_may,
        'danh_sach_loai_ca': danh_sach_loai_ca,
        'tong_thu_ca': tong_thu_ca,
        'thong_ke_may': {
            'trong': so_may_trong,
            'dang_chay': so_may_dang_chay,
            'hong': so_may_hong,
            'tong': danh_sach_may.count()
        },
        'hien_tai': timezone.now()
    }
    
    return render(request, 'quanly/pos.html', context)


# -----------------------------------------------------------------------------
# AJAX VIEWS CHO CÁC THAO TÁC
# -----------------------------------------------------------------------------

@login_required
def bat_dau_ca_ajax(request):
    """AJAX view để bắt đầu ca làm việc"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
    except NhanVien.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Không tìm thấy nhân viên'})
    
    # Kiểm tra ca đang chạy
    if CaLamViec.objects.filter(nhan_vien=nhan_vien, trang_thai='DANG_DIEN_RA').exists():
        return JsonResponse({'success': False, 'error': 'Bạn đã có ca đang chạy'})
    
    loai_ca_id = request.POST.get('loai_ca_id')
    tien_mat_str = request.POST.get('tien_mat_ban_dau', '0')
    
    try:
        loai_ca = LoaiCa.objects.get(pk=loai_ca_id)
        tien_mat_ban_dau = Decimal(tien_mat_str)
    except (LoaiCa.DoesNotExist, ValueError, decimal.InvalidOperation):
        return JsonResponse({'success': False, 'error': 'Dữ liệu không hợp lệ'})
    
    # Tạo ca mới
    ca_moi = CaLamViec.objects.create(
        nhan_vien=nhan_vien,
        loai_ca=loai_ca,
        tien_mat_ban_dau=tien_mat_ban_dau,
        thoi_gian_bat_dau_thuc_te=timezone.now(),
        ngay_lam_viec=timezone.now().date()
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'Đã bắt đầu {ca_moi.loai_ca.ten_ca}',
        'ca_id': ca_moi.id
    })


@login_required 
def mo_may_ajax(request, may_id):
    """AJAX view để mở máy"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
        
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        ca_hien_tai = CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai='DANG_DIEN_RA')
    except (NhanVien.DoesNotExist, CaLamViec.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Bạn phải bắt đầu ca trước khi mở máy'})
    
    try:
        may = May.objects.get(pk=may_id)
    except May.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Không tìm thấy máy'})
        
    if may.trang_thai != 'TRONG':
        return JsonResponse({'success': False, 'error': f'Máy {may.ten_may} không sẵn sàng'})
    
    # Kiểm tra phiên đang chạy (đề phòng)
    if PhienSuDung.objects.filter(may=may, trang_thai='DANG_DIEN_RA').exists():
        return JsonResponse({'success': False, 'error': 'Máy đã có phiên chạy'})
    
    # Tạo phiên mới
    phien_moi = PhienSuDung.objects.create(
        may=may,
        nhan_vien_mo_phien=nhan_vien,
        ca_lam_viec=ca_hien_tai,
        hinh_thuc='TRA_SAU'
    )
    
    # Cập nhật trạng thái máy
    may.trang_thai = 'DANG_SU_DUNG'
    may.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Đã mở máy {may.ten_may}',
        'phien_id': phien_moi.id
    })


@login_required
def ket_thuc_phien_ajax(request, phien_id):
    """AJAX view để kết thúc phiên và lập hóa đơn"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
        
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        ca_hien_tai = CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai='DANG_DIEN_RA')
    except (NhanVien.DoesNotExist, CaLamViec.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Không tìm thấy ca làm việc'})
    
    try:
        phien = PhienSuDung.objects.select_related('may__loai_may').get(
            pk=phien_id, 
            trang_thai='DANG_DIEN_RA'
        )
    except PhienSuDung.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Không tìm thấy phiên chạy'})
    
    # Kiểm tra quyền
    if phien.ca_lam_viec != ca_hien_tai:
        return JsonResponse({'success': False, 'error': 'Bạn không có quyền kết thúc phiên này'})
    
    # Tính tiền
    phien.thoi_gian_ket_thuc = timezone.now()
    duration_seconds = (phien.thoi_gian_ket_thuc - phien.thoi_gian_bat_dau).total_seconds()
    tien_gio = (Decimal(duration_seconds) / 3600) * phien.may.loai_may.don_gia_gio
    
    # Tính tiền dịch vụ (order chưa thanh toán)
    don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
    tien_dich_vu = don_hang_chua_tt.aggregate(total=Sum('tong_tien'))['total'] or Decimal('0.00')
    
    # Tạo hóa đơn
    hoa_don = HoaDon.objects.create(
        phien_su_dung=phien,
        ca_lam_viec=ca_hien_tai,
        tong_tien_gio=tien_gio,
        tong_tien_dich_vu=tien_dich_vu,
        tong_cong=tien_gio + tien_dich_vu,
        da_thanh_toan=True
    )
    
    # Ghi giao dịch tài chính
    GiaoDichTaiChinh.objects.create(
        ca_lam_viec=ca_hien_tai,
        hoa_don=hoa_don,
        khach_hang=phien.khach_hang,
        loai_giao_dich='THANH_TOAN_HOA_DON',
        so_tien=hoa_don.tong_cong
    )
    
    # Cập nhật trạng thái
    don_hang_chua_tt.update(da_thanh_toan=True)
    phien.trang_thai = 'DA_KET_THUC'
    phien.save()
    
    phien.may.trang_thai = 'TRONG'
    phien.may.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Đã kết thúc {phien.may.ten_may}',
        'hoa_don': {
            'id': hoa_don.id,
            'tong_tien': float(hoa_don.tong_cong),
            'tien_gio': float(tien_gio),
            'tien_dich_vu': float(tien_dich_vu)
        }
    })


@login_required
def ket_thuc_ca_ajax(request):
    """AJAX view để kết thúc ca làm việc"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
        
    try:
        nhan_vien = NhanVien.objects.get(tai_khoan=request.user)
        ca_hien_tai = CaLamViec.objects.get(nhan_vien=nhan_vien, trang_thai='DANG_DIEN_RA')
    except (NhanVien.DoesNotExist, CaLamViec.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Không tìm thấy ca đang chạy'})
    
    # Kiểm tra có phiên nào còn chạy không
    if PhienSuDung.objects.filter(ca_lam_viec=ca_hien_tai, trang_thai='DANG_DIEN_RA').exists():
        return JsonResponse({'success': False, 'error': 'Vẫn còn máy đang chạy trong ca này'})
    
    tien_mat_cuoi_ca_str = request.POST.get('tien_mat_cuoi_ca', '0')
    try:
        tien_mat_cuoi_ca = Decimal(tien_mat_cuoi_ca_str)
    except (ValueError, decimal.InvalidOperation):
        return JsonResponse({'success': False, 'error': 'Số tiền không hợp lệ'})
    
    # Tính doanh thu
    giao_dich_thu_tien = GiaoDichTaiChinh.objects.filter(
        ca_lam_viec=ca_hien_tai,
        loai_giao_dich__in=['THANH_TOAN_HOA_DON', 'THANH_TOAN_ORDER_LE', 'NAP_TIEN']
    )
    tong_doanh_thu = giao_dich_thu_tien.aggregate(total=Sum('so_tien'))['total'] or Decimal('0.00')
    
    # Tính chênh lệch
    tien_mat_ly_thuyet = ca_hien_tai.tien_mat_ban_dau + tong_doanh_thu
    chenh_lech = tien_mat_cuoi_ca - tien_mat_ly_thuyet
    
    # Cập nhật ca
    ca_hien_tai.thoi_gian_ket_thuc_thuc_te = timezone.now()
    ca_hien_tai.trang_thai = 'DA_KET_THUC'
    ca_hien_tai.tien_mat_cuoi_ca = tien_mat_cuoi_ca
    ca_hien_tai.tong_doanh_thu_he_thong = tong_doanh_thu
    ca_hien_tai.chenh_lech = chenh_lech
    ca_hien_tai.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Đã kết thúc ca làm việc',
        'ca_info': {
            'tong_doanh_thu': float(tong_doanh_thu),
            'tien_mat_cuoi_ca': float(tien_mat_cuoi_ca),
            'chenh_lech': float(chenh_lech)
        }
    })


# -----------------------------------------------------------------------------
# VIEW LẤY THÔNG TIN CHI TIẾT PHIÊN
# -----------------------------------------------------------------------------

@login_required
def chi_tiet_phien_ajax(request, phien_id):
    """AJAX view để lấy chi tiết phiên chạy"""
    try:
        phien = PhienSuDung.objects.select_related(
            'may__loai_may', 'khach_hang__tai_khoan'
        ).prefetch_related(
            'cac_don_hang__chi_tiet__mon'
        ).get(pk=phien_id, trang_thai='DANG_DIEN_RA')
    except PhienSuDung.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Không tìm thấy phiên'})
    
    # Tính thời gian chạy
    thoi_gian_chay = timezone.now() - phien.thoi_gian_bat_dau
    gio_chay = thoi_gian_chay.total_seconds() / 3600
    tien_gio_tam_tinh = Decimal(gio_chay) * phien.may.loai_may.don_gia_gio
    
    # Lấy danh sách order
    danh_sach_order = []
    for don_hang in phien.cac_don_hang.all():
        chi_tiet_order = []
        for chi_tiet in don_hang.chi_tiet.all():
            chi_tiet_order.append({
                'ten_mon': chi_tiet.mon.ten_mon,
                'so_luong': chi_tiet.so_luong,
                'thanh_tien': float(chi_tiet.thanh_tien)
            })
        
        danh_sach_order.append({
            'id': don_hang.id,
            'da_thanh_toan': don_hang.da_thanh_toan,
            'tong_tien': float(don_hang.tong_tien),
            'chi_tiet': chi_tiet_order
        })
    
    return JsonResponse({
        'success': True,
        'phien': {
            'id': phien.id,
            'ten_may': phien.may.ten_may,
            'loai_may': phien.may.loai_may.ten_loai,
            'don_gia_gio': float(phien.may.loai_may.don_gia_gio),
            'thoi_gian_bat_dau': phien.thoi_gian_bat_dau.strftime('%H:%M:%S'),
            'thoi_gian_chay_phut': int(thoi_gian_chay.total_seconds() / 60),
            'tien_gio_tam_tinh': float(tien_gio_tam_tinh),
            'hinh_thuc': phien.hinh_thuc,
            'khach_hang': phien.khach_hang.tai_khoan.username if phien.khach_hang else None,
            'danh_sach_order': danh_sach_order
        }
    })