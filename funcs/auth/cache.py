"""Cache state login lokal supaya user tidak harus validate ulang setiap launch.

Sesuai rekomendasi `FREE_PRODUCT_ACCESS.md` di repo vibetool, validasi cuma
ulang setiap 24 jam (TTL configurable). Cache TIDAK pernah menyimpan password —
hanya email, user_id, dan timestamp validate terakhir. Kalau user pindah mesin
atau hapus file ini, dia tinggal login ulang.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CACHE_FILENAME = "vibetool_auth.json"


@dataclass
class AuthState:
    email: str
    user_id: int
    name: str
    validated_at: str  # ISO-8601 UTC

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuthState":
        return cls(
            email=str(data.get("email", "")),
            user_id=int(data.get("user_id", 0) or 0),
            name=str(data.get("name", "")),
            validated_at=str(data.get("validated_at", "")),
        )

    @classmethod
    def now(cls, email: str, user_id: int, name: str) -> "AuthState":
        return cls(
            email=email,
            user_id=user_id,
            name=name,
            validated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def is_fresh(self, ttl_hours: int, now: Optional[datetime] = None) -> bool:
        """True kalau validated_at masih dalam window TTL."""
        ts = _parse_iso(self.validated_at)
        if ts is None:
            return False
        if now is None:
            now = datetime.now(timezone.utc)
        age = now - ts
        return age.total_seconds() < ttl_hours * 3600


class AuthCache:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Optional[AuthState]:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        state = AuthState.from_dict(data)
        if not state.email or not state.validated_at:
            return None
        return state

    def save(self, state: AuthState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".vibetool_auth.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(state.to_dict(), fh, indent=2)
            os.replace(tmp_path, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                # Windows / filesystem yang tidak support chmod — abaikan.
                pass
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def default_cache_path() -> Path:
    """Folder kerja aplikasi (sama dengan tempat sessions/, members.csv, dll)."""
    return Path.cwd() / CACHE_FILENAME
