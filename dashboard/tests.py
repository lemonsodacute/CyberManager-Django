from types import SimpleNamespace

from django.test import SimpleTestCase

from quanly.permissions import IsAdminRole


class DashboardPermissionTest(SimpleTestCase):
    def test_superuser_duoc_truy_cap(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=True)
        self.assertTrue(IsAdminRole().has_permission(SimpleNamespace(user=user), None))

    def test_khach_hang_khong_duoc_truy_cap(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        self.assertFalse(IsAdminRole().has_permission(SimpleNamespace(user=user), None))

    def test_chua_dang_nhap_bi_tu_choi(self):
        user = SimpleNamespace(is_authenticated=False)
        self.assertFalse(IsAdminRole().has_permission(SimpleNamespace(user=user), None))
