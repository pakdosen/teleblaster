"""Konfigurasi VibeTool API untuk login gate.

Default-nya menunjuk ke https://vibetool.id production. Semua nilai bisa
diganti lewat `.env` (file yang sama dipakai untuk API_ID/API_HASH Telegram)
tanpa rebuild.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://vibetool.id"
DEFAULT_PRODUCT_SLUG = "teleblaster"
DEFAULT_TIMEOUT = 15.0
# Cache valid sebelum re-validate ke API. Sesuai rekomendasi
# `FREE_PRODUCT_ACCESS.md` di repo dirazerita/vibetool.
DEFAULT_TTL_HOURS = 24


@dataclass(frozen=True)
class VibetoolConfig:
    base_url: str = DEFAULT_BASE_URL
    product_slug: str = DEFAULT_PRODUCT_SLUG
    timeout: float = DEFAULT_TIMEOUT
    ttl_hours: int = DEFAULT_TTL_HOURS

    @property
    def validate_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/auth/validate-member"

    @property
    def register_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/auth/register"

    @property
    def whatsapp_admin_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/setting/whatsapp-admin"

    @property
    def web_register_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/register"

    @classmethod
    def from_env(cls) -> "VibetoolConfig":
        base = os.getenv("VIBETOOL_BASE_URL", "").strip() or DEFAULT_BASE_URL
        slug = os.getenv("VIBETOOL_PRODUCT_SLUG", "").strip() or DEFAULT_PRODUCT_SLUG
        timeout_raw = os.getenv("VIBETOOL_TIMEOUT", "").strip()
        ttl_raw = os.getenv("VIBETOOL_TTL_HOURS", "").strip()

        try:
            timeout = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT
        except ValueError:
            timeout = DEFAULT_TIMEOUT

        try:
            ttl_hours = int(ttl_raw) if ttl_raw else DEFAULT_TTL_HOURS
        except ValueError:
            ttl_hours = DEFAULT_TTL_HOURS

        return cls(base_url=base, product_slug=slug, timeout=timeout, ttl_hours=ttl_hours)
