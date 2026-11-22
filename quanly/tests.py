from types import SimpleNamespace

from django.test import SimpleTestCase

from accounts.models import TaiKhoan
from .permissions import IsNhanVien


class PhanQuyenPOSTest(SimpleTestCase):
    def test_nhan_vien_duoc_vao_pos(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            loai_tai_khoan=TaiKhoan.LoaiTaiKhoan.NHAN_VIEN,
        )
        self.assertTrue(IsNhanVien().has_permission(SimpleNamespace(user=user), None))

    def test_admin_thuong_khong_vao_pos(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            loai_tai_khoan=TaiKhoan.LoaiTaiKhoan.ADMIN,
        )
        self.assertFalse(IsNhanVien().has_permission(SimpleNamespace(user=user), None))

    def test_chua_dang_nhap_bi_tu_choi(self):
        user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(IsNhanVien().has_permission(SimpleNamespace(user=user), None))

    def test_superuser_duoc_vao_pos(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=True)
        self.assertTrue(IsNhanVien().has_permission(SimpleNamespace(user=user), None))
