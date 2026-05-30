"""Entry point auth gate yang dipanggil dari gui_app.py.

Flow:
  1. Coba load cache. Kalau ada & belum expired → langsung lewat (skip login).
  2. Kalau cache expired / kosong → tampilkan LoginWindow.
  3. Tunggu user login berhasil atau tutup window.

Return True kalau autentikasi sukses; False kalau user batal / tutup tanpa
login. Caller bertanggung jawab nutup `root` saat False supaya app keluar.
"""

from __future__ import annotations

import tkinter as tk

from .cache import AuthCache, default_cache_path
from .client import VibetoolClient
from .config import VibetoolConfig
from .login_window import LoginWindow


def ensure_authenticated(root: tk.Misc) -> bool:
    config = VibetoolConfig.from_env()
    client = VibetoolClient(config)
    cache = AuthCache(default_cache_path())

    state = cache.load()
    if state and state.is_fresh(ttl_hours=config.ttl_hours):
        return True

    prefill = state.email if state else ""
    window = LoginWindow(root, client=client, cache=cache, prefill_email=prefill)
    root.wait_window(window)
    return window.success
