"""Pembatasan fitur untuk versi gratis Telegram Blaster.

Tujuan modul ini adalah memusatkan semua aturan "free vs pro":

- ``MAX_TELEGRAM_ACCOUNTS = 1`` → hanya boleh ada satu session Telegram aktif.
- Tab ``Members Adder`` dan ``Grup Scrapper`` dinonaktifkan dan menampilkan
  popup upgrade ketika user mencoba klik.

Membungkus semua aturan di satu file memudahkan kita kelak mengangkat
pembatasan saat upgrade ke Pro (misal: dari validate-member response).
"""

from __future__ import annotations

from tkinter import messagebox
from typing import Optional


MAX_TELEGRAM_ACCOUNTS = 1

DISABLED_TABS = ("Members Adder", "Grup Scrapper")

_UPGRADE_BODY = (
    "Free version hanya bisa untuk satu akun Telegram.\n\n"
    "Upgrade ke versi Pro untuk membuka full fitur:\n"
    "  • Multi-akun (rotasi tanpa batas)\n"
    "  • Members Adder\n"
    "  • Grup Scrapper\n\n"
    "Hubungi admin di vibetool.id untuk upgrade."
)


def upgrade_required_message() -> str:
    """Pesan popup standar untuk fitur yang terkunci di Free version."""
    return _UPGRADE_BODY


def show_upgrade_popup(parent=None, title: str = "Upgrade ke Pro Diperlukan") -> None:
    """Tampilkan popup info bahwa fitur tersebut hanya tersedia di Pro."""
    messagebox.showinfo(title, _UPGRADE_BODY, parent=parent)


def is_account_limit_reached(current_session_count: int) -> bool:
    """Apakah user sudah mencapai batas akun Telegram di Free version."""
    return current_session_count >= MAX_TELEGRAM_ACCOUNTS


def block_if_account_limit_reached(
    current_session_count: int,
    parent=None,
) -> bool:
    """Tampilkan popup + return True kalau limit sudah tercapai.

    Caller wajib early-return kalau fungsi ini balik ``True``.
    """
    if is_account_limit_reached(current_session_count):
        show_upgrade_popup(
            parent=parent,
            title="Batas Akun Telegram Tercapai (Free Version)",
        )
        return True
    return False


def is_tab_disabled(tab_text: str) -> bool:
    """True kalau tab tersebut dinonaktifkan di Free version."""
    return tab_text in DISABLED_TABS


__all__ = [
    "MAX_TELEGRAM_ACCOUNTS",
    "DISABLED_TABS",
    "upgrade_required_message",
    "show_upgrade_popup",
    "is_account_limit_reached",
    "block_if_account_limit_reached",
    "is_tab_disabled",
]
