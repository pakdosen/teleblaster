"""Tests untuk funcs.auth.client.VibetoolClient.

Mock urllib.request.urlopen supaya tidak bikin koneksi internet beneran.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from funcs.auth.client import VibetoolClient
from funcs.auth.config import VibetoolConfig


def _http_response(status: int, body: dict | str):
    """Fake urllib.urlopen() response context manager."""
    raw = json.dumps(body).encode("utf-8") if isinstance(body, dict) else body.encode("utf-8")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def getcode(self):
            return status

        def read(self):
            return raw

    return FakeResp()


def _http_error(status: int, body: dict):
    return urllib.error.HTTPError(
        url="https://example.com/x",
        code=status,
        msg="error",
        hdrs={},
        fp=io.BytesIO(json.dumps(body).encode("utf-8")),
    )


class VibetoolClientValidateTest(unittest.TestCase):
    def setUp(self):
        self.client = VibetoolClient(VibetoolConfig(base_url="https://example.com", product_slug="teleblaster"))

    def test_valid_credentials(self):
        body = {
            "valid": True,
            "message": "OK",
            "user": {"id": 1, "name": "Alice", "email": "a@b.com"},
            "product": {"id": 10, "title": "TB", "slug": "teleblaster", "type": "free"},
        }
        with mock.patch("urllib.request.urlopen", return_value=_http_response(200, body)):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertTrue(result.valid)
        self.assertEqual(result.user["email"], "a@b.com")

    def test_invalid_credentials(self):
        body = {"valid": False, "error": "invalid_credentials", "message": "Email atau password salah."}
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(401, body)):
            result = self.client.validate_member("a@b.com", "wrong")
        self.assertFalse(result.valid)
        self.assertEqual(result.error_code, "invalid_credentials")
        self.assertEqual(result.http_status, 401)

    def test_account_inactive(self):
        body = {"valid": False, "error": "account_inactive", "message": "Akun belum aktif."}
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(403, body)):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertFalse(result.valid)
        self.assertTrue(result.is_account_inactive)

    def test_no_access(self):
        body = {"valid": False, "error": "no_access", "message": "Belum klaim produk."}
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(403, body)):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertTrue(result.is_no_access)

    def test_product_not_found(self):
        body = {"valid": False, "error": "product_not_found", "message": "..."}
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(404, body)):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertEqual(result.error_code, "product_not_found")

    def test_rate_limited(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(429, {})):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertEqual(result.error_code, "rate_limited")

    def test_network_error_returns_network_code(self):
        err = urllib.error.URLError("Connection refused")
        with mock.patch("urllib.request.urlopen", side_effect=err):
            result = self.client.validate_member("a@b.com", "pw")
        self.assertFalse(result.valid)
        self.assertEqual(result.error_code, "network")


class VibetoolClientRegisterTest(unittest.TestCase):
    def setUp(self):
        self.client = VibetoolClient(VibetoolConfig(base_url="https://example.com"))

    def test_register_success_201(self):
        body = {"ok": True, "status": "pending", "user": {"id": 1, "name": "A", "email": "a@b.com", "whatsapp_number": "62812"}}
        with mock.patch("urllib.request.urlopen", return_value=_http_response(201, body)):
            result = self.client.register("A", "a@b.com", "081234", "pw12345!", "pw12345!")
        self.assertTrue(result.ok)
        self.assertEqual(result.user["email"], "a@b.com")

    def test_register_validation_error_422(self):
        body = {
            "ok": False,
            "error": "validation_error",
            "message": "Data tidak valid.",
            "errors": {"email": ["Email sudah dipakai."]},
        }
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(422, body)):
            result = self.client.register("A", "a@b.com", "081234", "pw", "pw")
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "validation_error")
        self.assertIn("email", result.field_errors)

    def test_register_rate_limited(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(429, {})):
            result = self.client.register("A", "a@b.com", "081234", "pw", "pw")
        self.assertEqual(result.error_code, "rate_limited")


class VibetoolClientAdminWhatsAppTest(unittest.TestCase):
    def setUp(self):
        self.client = VibetoolClient(VibetoolConfig(base_url="https://example.com"))

    def test_fetch_admin_success(self):
        with mock.patch("urllib.request.urlopen", return_value=_http_response(200, {"number": "6281234567890"})):
            result = self.client.fetch_whatsapp_admin()
        self.assertEqual(result.number, "6281234567890")

    def test_fetch_admin_not_configured(self):
        with mock.patch("urllib.request.urlopen", side_effect=_http_error(404, {"number": None})):
            result = self.client.fetch_whatsapp_admin()
        self.assertIsNone(result.number)
        self.assertEqual(result.error_code, "not_configured")


class BuildActivationWaLinkTest(unittest.TestCase):
    def test_link_contains_wa_me_and_admin_number(self):
        link = VibetoolClient.build_activation_wa_link(
            admin_number="6281234567890",
            name="Alice",
            email="a@b.com",
            whatsapp_number="6281122334455",
        )
        self.assertTrue(link.startswith("https://wa.me/6281234567890?text="))
        self.assertIn("Alice", link)
        self.assertIn("a%40b.com", link)
        self.assertIn("6281122334455", link)

    def test_link_handles_missing_whatsapp_number(self):
        link = VibetoolClient.build_activation_wa_link(
            admin_number="62888",
            name="A",
            email="a@b.com",
            whatsapp_number=None,
        )
        # "-" placeholder dipakai saat WA kosong.
        self.assertIn("-", link)


if __name__ == "__main__":
    unittest.main()
