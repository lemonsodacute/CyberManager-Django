from django.test import SimpleTestCase

from .models import TaiKhoan


class TaiKhoanTest(SimpleTestCase):
    def test_tai_khoan_moi_mac_dinh_la_khach_hang(self):
        user = TaiKhoan(username="khach01")
        self.assertEqual(user.loai_tai_khoan, TaiKhoan.LoaiTaiKhoan.KHACH_HANG)

    def test_hien_thi_ten_dang_nhap(self):
        user = TaiKhoan(username="nhanvien01")
        self.assertEqual(str(user), "nhanvien01")
