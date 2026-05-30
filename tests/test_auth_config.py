"""Tests untuk funcs.auth.config.VibetoolConfig."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from funcs.auth.config import (
    DEFAULT_BASE_URL,
    DEFAULT_PRODUCT_SLUG,
    DEFAULT_TIMEOUT,
    DEFAULT_TTL_HOURS,
    VibetoolConfig,
)


class VibetoolConfigTest(unittest.TestCase):
    def test_defaults_when_env_empty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = VibetoolConfig.from_env()
        self.assertEqual(cfg.base_url, DEFAULT_BASE_URL)
        self.assertEqual(cfg.product_slug, DEFAULT_PRODUCT_SLUG)
        self.assertEqual(cfg.timeout, DEFAULT_TIMEOUT)
        self.assertEqual(cfg.ttl_hours, DEFAULT_TTL_HOURS)

    def test_overrides_from_env(self):
        env = {
            "VIBETOOL_BASE_URL": "http://localhost:8000",
            "VIBETOOL_PRODUCT_SLUG": "custom-slug",
            "VIBETOOL_TIMEOUT": "30.5",
            "VIBETOOL_TTL_HOURS": "12",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = VibetoolConfig.from_env()
        self.assertEqual(cfg.base_url, "http://localhost:8000")
        self.assertEqual(cfg.product_slug, "custom-slug")
        self.assertEqual(cfg.timeout, 30.5)
        self.assertEqual(cfg.ttl_hours, 12)

    def test_invalid_timeout_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"VIBETOOL_TIMEOUT": "not-a-number"}, clear=True):
            cfg = VibetoolConfig.from_env()
        self.assertEqual(cfg.timeout, DEFAULT_TIMEOUT)

    def test_invalid_ttl_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {"VIBETOOL_TTL_HOURS": "abc"}, clear=True):
            cfg = VibetoolConfig.from_env()
        self.assertEqual(cfg.ttl_hours, DEFAULT_TTL_HOURS)

    def test_trailing_slash_stripped_in_urls(self):
        cfg = VibetoolConfig(base_url="https://example.com/")
        self.assertEqual(cfg.validate_url, "https://example.com/api/auth/validate-member")
        self.assertEqual(cfg.register_url, "https://example.com/api/auth/register")
        self.assertEqual(cfg.whatsapp_admin_url, "https://example.com/api/setting/whatsapp-admin")
        self.assertEqual(cfg.web_register_url, "https://example.com/register")


if __name__ == "__main__":
    unittest.main()
