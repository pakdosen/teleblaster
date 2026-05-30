"""Tema gelap + branding logo untuk window auth (Login + Register).

Palet warna disamakan dengan tema gelap default GUI utama (lihat
``TelegramScraperGUI.themes['dark']`` di ``gui_app.py``) supaya transisi
dari login → GUI utama tidak terasa "lompat".

Modul ini menyediakan:
- ``DARK_COLORS``: dict warna.
- ``apply_auth_theme(window)``: setup ttk styles dengan prefix ``Auth.*``
  yang hanya dipakai window auth, sehingga tidak bentrok dengan tema GUI
  utama yang di-setup ulang setelah login berhasil.
- ``load_logo(size)``: cache loader untuk ``assets/vibetool_logo.png``.
- ``apply_window_icon(window)``: pasang icon window dari logo PNG/ICO.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Optional


DARK_COLORS = {
    "bg": "#0b0f17",
    "panel": "#141a26",
    "panel_2": "#1d2533",
    "panel_3": "#252e3f",
    "text": "#ecf1f8",
    "muted": "#94a3b8",
    "accent": "#5ea0ff",
    "accent_hover": "#7cb3ff",
    "accent_press": "#3d8aff",
    "border": "#2a3447",
    "ok": "#34d399",
    "danger": "#ef5d6f",
    "warn": "#f5b454",
}


def _assets_dir() -> Path:
    """Lokasi folder ``assets/`` repo. Handle PyInstaller _MEIPASS juga."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "assets"
        if candidate.exists():
            return candidate
    # funcs/auth/theme.py → naik 2 level ke repo root.
    return Path(__file__).resolve().parent.parent.parent / "assets"


_LOGO_PNG = _assets_dir() / "vibetool_logo.png"
_LOGO_ICO = _assets_dir() / "vibetool_logo.ico"


_logo_cache: dict[int, Any] = {}


def load_logo(size: int) -> Optional[Any]:
    """Return ``ImageTk.PhotoImage`` ukuran ``size x size`` (cached).

    Mengembalikan ``None`` kalau Pillow tidak terinstall atau file PNG
    tidak ada — caller harus handle None tanpa crash.
    """
    if size in _logo_cache:
        return _logo_cache[size]
    try:
        from PIL import Image, ImageTk  # type: ignore[import-not-found]

        if not _LOGO_PNG.exists():
            return None
        img = Image.open(_LOGO_PNG).convert("RGBA").resize((size, size), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
    except Exception:
        return None
    _logo_cache[size] = photo
    return photo


def apply_window_icon(window: tk.Misc) -> None:
    """Pasang icon window dari ``vibetool_logo``. Best-effort, ignore error."""
    # Coba .ico dulu (taskbar Windows lebih bagus dengan ICO).
    try:
        if _LOGO_ICO.exists():
            window.iconbitmap(default=str(_LOGO_ICO))
            return
    except Exception:
        pass
    photo = load_logo(64)
    if photo is not None:
        try:
            window.iconphoto(True, photo)
        except Exception:
            pass


_styles_initialized: dict[int, bool] = {}


def apply_auth_theme(window: tk.Misc) -> None:
    """Set background gelap pada ``window`` + register style ``Auth.*``.

    Style hanya didaftarkan sekali per Tk root (ttk.Style global per
    interpreter). Background window selalu di-set ulang supaya konsisten.
    """
    c = DARK_COLORS
    try:
        window.configure(bg=c["bg"])
    except Exception:
        pass

    style = ttk.Style(window)
    try:
        style.theme_use("clam")  # 'clam' paling konsisten untuk override warna.
    except Exception:
        pass

    root_id = id(window.tk)
    if _styles_initialized.get(root_id):
        return
    _styles_initialized[root_id] = True

    ui_font = ("Segoe UI", 10)
    header_font = ("Segoe UI Semibold", 18)
    sub_font = ("Segoe UI", 10)
    btn_font = ("Segoe UI", 10)
    accent_btn_font = ("Segoe UI Semibold", 11)

    # Frames
    style.configure("Auth.TFrame", background=c["bg"])

    # Labels
    style.configure(
        "Auth.TLabel",
        background=c["bg"],
        foreground=c["text"],
        font=ui_font,
    )
    style.configure(
        "AuthHeader.TLabel",
        background=c["bg"],
        foreground=c["text"],
        font=header_font,
    )
    style.configure(
        "AuthSub.TLabel",
        background=c["bg"],
        foreground=c["muted"],
        font=sub_font,
    )
    style.configure(
        "AuthMuted.TLabel",
        background=c["bg"],
        foreground=c["muted"],
        font=("Segoe UI", 9),
    )
    style.configure(
        "AuthError.TLabel",
        background=c["bg"],
        foreground=c["danger"],
        font=("Segoe UI", 9),
    )
    style.configure(
        "AuthOk.TLabel",
        background=c["bg"],
        foreground=c["ok"],
        font=("Segoe UI Semibold", 10),
    )

    # Entry — pakai ttk.Entry dengan style "Auth.TEntry". Field warnanya
    # panel_2, text terang, border halus.
    style.configure(
        "Auth.TEntry",
        fieldbackground=c["panel_2"],
        foreground=c["text"],
        insertcolor=c["text"],
        bordercolor=c["border"],
        lightcolor=c["border"],
        darkcolor=c["border"],
        padding=6,
    )
    style.map(
        "Auth.TEntry",
        fieldbackground=[("readonly", c["panel"]), ("disabled", c["panel"])],
        foreground=[("disabled", c["muted"])],
        bordercolor=[("focus", c["accent"])],
        lightcolor=[("focus", c["accent"])],
        darkcolor=[("focus", c["accent"])],
    )

    # Buttons — varian default (subtle) + accent (primary)
    style.configure(
        "Auth.TButton",
        background=c["panel_2"],
        foreground=c["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 8),
        font=btn_font,
    )
    style.map(
        "Auth.TButton",
        background=[
            ("active", c["panel_3"]),
            ("pressed", c["panel_3"]),
            ("disabled", c["panel_2"]),
        ],
        foreground=[("disabled", c["muted"])],
    )

    style.configure(
        "AuthAccent.TButton",
        background=c["accent"],
        foreground="#0a1220",
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
        font=accent_btn_font,
    )
    style.map(
        "AuthAccent.TButton",
        background=[
            ("active", c["accent_hover"]),
            ("pressed", c["accent_press"]),
            ("disabled", c["panel_2"]),
        ],
        foreground=[("disabled", c["muted"])],
    )

    style.configure(
        "AuthOk.TButton",
        background=c["ok"],
        foreground="#0a1220",
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
        font=accent_btn_font,
    )
    style.map(
        "AuthOk.TButton",
        background=[("active", "#4ade8b"), ("pressed", c["ok"])],
    )
