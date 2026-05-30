"""HTTP client untuk endpoint publik vibetool.id.

Setiap method mengembalikan objek hasil terstruktur — bukan raise — supaya
caller di Tkinter UI gampang nampilin popup yang tepat per kasus error.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from .config import VibetoolConfig


USER_AGENT = "TeleBlaster-LoginGate/1.0"


@dataclass
class ValidationResult:
    """Hasil POST /api/auth/validate-member."""

    valid: bool
    error_code: Optional[str] = None  # invalid_credentials | account_inactive | no_access | product_not_found | rate_limited | network | unknown
    message: str = ""
    http_status: Optional[int] = None
    user: Optional[dict] = None
    product: Optional[dict] = None

    @property
    def is_account_inactive(self) -> bool:
        return self.error_code == "account_inactive"

    @property
    def is_no_access(self) -> bool:
        return self.error_code == "no_access"


@dataclass
class RegisterResult:
    """Hasil POST /api/auth/register."""

    ok: bool
    error_code: Optional[str] = None  # validation_error | rate_limited | network | unknown
    message: str = ""
    http_status: Optional[int] = None
    user: Optional[dict] = None
    field_errors: dict = field(default_factory=dict)


@dataclass
class WhatsAppAdminResult:
    number: Optional[str] = None
    error_code: Optional[str] = None  # not_configured | network | unknown
    message: str = ""


class VibetoolClient:
    """Thin HTTP client. Pakai stdlib urllib supaya tidak nambah dependency
    selain yang sudah ada di requirements.txt."""

    def __init__(self, config: VibetoolConfig):
        self.config = config

    # ---------- public methods ----------

    def validate_member(self, email: str, password: str) -> ValidationResult:
        body = {
            "email": email,
            "password": password,
            "product_slug": self.config.product_slug,
        }
        status, data = self._post_json(self.config.validate_url, body)
        if status is None:
            return ValidationResult(valid=False, error_code="network", message=data or "Tidak bisa terhubung ke server.")

        if status == 200 and isinstance(data, dict) and data.get("valid"):
            return ValidationResult(
                valid=True,
                http_status=status,
                message=data.get("message", "Akses valid."),
                user=data.get("user"),
                product=data.get("product"),
            )

        if status == 429:
            return ValidationResult(
                valid=False,
                error_code="rate_limited",
                http_status=status,
                message="Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi.",
            )

        # Server merespons error spesifik (401/403/404).
        if isinstance(data, dict):
            return ValidationResult(
                valid=False,
                error_code=data.get("error") or "unknown",
                http_status=status,
                message=data.get("message") or "Login gagal.",
            )

        return ValidationResult(
            valid=False,
            error_code="unknown",
            http_status=status,
            message=f"Respons server tidak terduga (HTTP {status}).",
        )

    def register(
        self,
        name: str,
        email: str,
        whatsapp_number: str,
        password: str,
        password_confirmation: str,
    ) -> RegisterResult:
        body = {
            "name": name,
            "email": email,
            "whatsapp_number": whatsapp_number,
            "password": password,
            "password_confirmation": password_confirmation,
        }
        status, data = self._post_json(self.config.register_url, body)
        if status is None:
            return RegisterResult(ok=False, error_code="network", message=data or "Tidak bisa terhubung ke server.")

        if status in (200, 201) and isinstance(data, dict) and data.get("ok"):
            return RegisterResult(
                ok=True,
                http_status=status,
                message=data.get("message", "Registrasi berhasil."),
                user=data.get("user"),
            )

        if status == 429:
            return RegisterResult(
                ok=False,
                error_code="rate_limited",
                http_status=status,
                message="Terlalu banyak pendaftaran. Tunggu sebentar lalu coba lagi.",
            )

        if status == 422 and isinstance(data, dict):
            errors = data.get("errors") or {}
            # Flatten per-field error list jadi pesan ringkas.
            field_errors = {}
            if isinstance(errors, dict):
                for field_name, messages in errors.items():
                    if isinstance(messages, list) and messages:
                        field_errors[field_name] = str(messages[0])
                    elif isinstance(messages, str):
                        field_errors[field_name] = messages
            return RegisterResult(
                ok=False,
                error_code="validation_error",
                http_status=status,
                message=data.get("message", "Data tidak valid. Periksa kembali isian."),
                field_errors=field_errors,
            )

        message = "Registrasi gagal."
        if isinstance(data, dict):
            message = data.get("message", message)
        return RegisterResult(
            ok=False,
            error_code="unknown",
            http_status=status,
            message=message,
        )

    def fetch_whatsapp_admin(self) -> WhatsAppAdminResult:
        status, data = self._get_json(self.config.whatsapp_admin_url)
        if status is None:
            return WhatsAppAdminResult(error_code="network", message=data or "Tidak bisa terhubung ke server.")

        if status == 200 and isinstance(data, dict) and data.get("number"):
            return WhatsAppAdminResult(number=str(data["number"]))

        if status == 404:
            return WhatsAppAdminResult(
                error_code="not_configured",
                message="Nomor admin WhatsApp belum dikonfigurasi di vibetool.id.",
            )

        return WhatsAppAdminResult(
            error_code="unknown",
            message=f"Respons server tidak terduga (HTTP {status}).",
        )

    @staticmethod
    def build_activation_wa_link(
        admin_number: str,
        name: str,
        email: str,
        whatsapp_number: Optional[str] = None,
    ) -> str:
        """Format URL wa.me sesuai pesan default vibetool.id."""

        lines = [
            "Halo Admin VibeTool 👋",
            "Saya ingin mengaktifkan membership saya.",
            "",
            f"Nama: {name}",
            f"Email: {email}",
            f"No WA: {whatsapp_number or '-'}",
            "",
            "Mohon akun saya diaktifkan. Terima kasih!",
        ]
        text = "\n".join(lines)
        return f"https://wa.me/{admin_number}?text={urllib.parse.quote(text)}"

    # ---------- internal helpers ----------

    def _post_json(self, url: str, body: dict) -> tuple[Optional[int], Any]:
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        return self._send(req)

    def _get_json(self, url: str) -> tuple[Optional[int], Any]:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        return self._send(req)

    def _send(self, req: urllib.request.Request) -> tuple[Optional[int], Any]:
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                status = resp.getcode()
                raw = resp.read().decode("utf-8", errors="replace")
                return status, _safe_json(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            return e.code, _safe_json(raw)
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            return None, f"Koneksi gagal: {reason}"
        except TimeoutError:
            return None, "Koneksi timeout."
        except Exception as e:  # noqa: BLE001
            return None, f"Error: {e}"


def _safe_json(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
