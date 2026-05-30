"""Login gate untuk validasi akses lewat akun member VibeTool.id.

Modul ini menambahkan langkah autentikasi sebelum GUI utama Telegram Blaster
terbuka. User harus login dengan akun yang sudah terdaftar & aktif di
https://vibetool.id (dan sudah klaim produk gratis Telegram Blaster).

Public entry point:
    ensure_authenticated(root) -> bool

Note: `ensure_authenticated` di-import lazy supaya submodul non-GUI
(client/config/cache) bisa di-import & dites tanpa membutuhkan Tk.
"""

from typing import TYPE_CHECKING, Any

__all__ = ["ensure_authenticated"]


def ensure_authenticated(root: "Any") -> bool:
    from .gate import ensure_authenticated as _impl

    return _impl(root)


if TYPE_CHECKING:
    from .gate import ensure_authenticated  # noqa: F401
