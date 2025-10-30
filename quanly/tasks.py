import os
import logging
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    CaLamViec,
    PhienSuDung,
    KhachHang,
    HoaDon,
    GiaoDichTaiChinh,
    May,
    ChiTietDonHang,
    DonHangDichVu,
    KhuyenMai,
    LichSuThayDoiKho,
)
from .api_views import DashboardSummaryAPIView

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# ==============================
# ⚙️ Thiết lập logging
# ==============================
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "auto_shutdown.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),  # In ra console luôn
    ],
)
logger = logging.getLogger(__name__)


# ==============================
# 💡 Hàm chính: Tự động ngắt phiên trả trước
# ==============================
def auto_shutdown_prepaid_sessions():
    """
    Tự động kiểm tra và ngắt các phiên trả trước (TRA_TRUOC)
    khi số dư khách hàng không còn đủ để tiếp tục sử dụng.
    """

    shutdown_count = 0
    current_time = timezone.now()

    # Đảm bảo toàn bộ thao tác nằm trong transaction
    with transaction.atomic():
        sessions_to_check = (
            PhienSuDung.objects.select_for_update()
            .select_related("may__loai_may", "khach_hang__tai_khoan")
            .filter(
                trang_thai=PhienSuDung.TrangThai.DANG_DIEN_RA,
                hinh_thuc=PhienSuDung.HinhThuc.TRA_TRUOC,
                khach_hang__isnull=False,
            )
            .prefetch_related("cac_don_hang__chi_tiet")
        )

        if not sessions_to_check.exists():
            return 0

        for phien in sessions_to_check:
            try:
                with transaction.atomic():
                    may = phien.may
                    khach_hang = phien.khach_hang

                    # ===== A. TÍNH TOÁN CHI PHÍ HIỆN TẠI =====
                    duration_seconds = (current_time - phien.thoi_gian_bat_dau).total_seconds()
                    duration_hours = Decimal(duration_seconds) / Decimal(3600)
                    tien_gio_hien_tai = duration_hours * may.loai_may.don_gia_gio

                    don_hang_chua_tt = phien.cac_don_hang.filter(da_thanh_toan=False)
                    tien_dich_vu_chua_tt = (
                        don_hang_chua_tt.aggregate(total=Sum("tong_tien"))["total"]
                        or Decimal("0.00")
                    )

                    tong_chi_phi = tien_gio_hien_tai + tien_dich_vu_chua_tt

                    # ===== B. KIỂM TRA SỐ DƯ KHÁCH HÀNG =====
                    if khach_hang.so_du <= (tong_chi_phi - Decimal("1")):
                        # 1️⃣ CẬP NHẬT TRẠNG THÁI PHIÊN & MÁY
                        phien.thoi_gian_ket_thuc = current_time
                        phien.trang_thai = PhienSuDung.TrangThai.DA_KET_THUC
                        may.trang_thai = May.TrangThai.TRONG
                        may.save(update_fields=["trang_thai"])
                        phien.save(update_fields=["thoi_gian_ket_thuc", "trang_thai"])

                        # 2️⃣ TẠO HÓA ĐƠN
                        tong_tien_giam_gia = (
                            don_hang_chua_tt.aggregate(total=Sum("tien_giam_gia"))["total"]
                            or Decimal("0.00")
                        )

                        hoa_don = HoaDon.objects.create(
                            phien_su_dung=phien,
                            ca_lam_viec=phien.ca_lam_viec,
                            tong_tien_gio=tien_gio_hien_tai,
                            tong_tien_dich_vu=tien_dich_vu_chua_tt,
                            tien_giam_gia=tong_tien_giam_gia,
                            tong_cong=tong_chi_phi,
                            da_thanh_toan=True,
                        )

                        # 3️⃣ TRỪ TIỀN KHÁCH HÀNG
                        KhachHang.objects.filter(pk=khach_hang.pk).update(
                            so_du=F("so_du") - tong_chi_phi
                        )

                        # 4️⃣ GHI NHẬN GIAO DỊCH
                        GiaoDichTaiChinh.objects.create(
                            ca_lam_viec=phien.ca_lam_viec,
                            hoa_don=hoa_don,
                            khach_hang=khach_hang,
                            loai_giao_dich=GiaoDichTaiChinh.LoaiGiaoDich.THANH_TOAN_TK,
                            so_tien=tong_chi_phi,
                        )

                        # 5️⃣ CẬP NHẬT DOANH THU VÀO CA LÀM VIỆC
                        CaLamViec.objects.filter(pk=phien.ca_lam_viec.pk).update(
                            tong_doanh_thu_he_thong=F("tong_doanh_thu_he_thong") + tong_chi_phi
                        )

                        # 6️⃣ ĐÁNH DẤU ĐƠN HÀNG DỊCH VỤ ĐÃ THANH TOÁN
                        don_hang_chua_tt.update(da_thanh_toan=True)

                        # 7️⃣ GỬI THÔNG BÁO WEBSOCKET
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            "dashboard_summary",
                            {
                                "type": "send_summary_update",
                                "data": DashboardSummaryAPIView().calculate_summary(),
                            },
                        )

                      
                      # 8️⃣ GHI LOG
                        logger.info(
                            f"[AUTO SHUTDOWN] Đã ngắt máy {may.ten_may} - "
                            f"Khách: {khach_hang.username} - "  # <<< ĐÃ SỬA TỪ .ten_khach THÀNH .username
                            f"Tổng phí: {tong_chi_phi:,.0f}₫ - "
                            f"Ca: {phien.ca_lam_viec.id}"
                        )

                        shutdown_count += 1

                    else:
                        # Nếu khách hàng còn tiền, chỉ cập nhật thời gian kiểm tra
                        phien.thoi_gian_kiem_tra_lan_cuoi = current_time
                        phien.save(update_fields=["thoi_gian_kiem_tra_lan_cuoi"])

            except ObjectDoesNotExist as e:
                logger.warning(f"[WARN] Lỗi dữ liệu phiên #{phien.id}: {e}")
            except Exception as e:
                logger.error(f"[ERROR] Lỗi khi xử lý phiên #{phien.id}: {e}")

    return shutdown_count
