"""Window login VibeTool yang muncul sebelum GUI utama Telegram Blaster.

UI didesain minimalis dengan 4 aksi utama: Login, Daftar di Sini (in-app),
Daftar di Website (browser), Hubungi Admin via WhatsApp. Hasil login
dikembalikan ke caller lewat callback `on_success`.
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Optional

from .cache import AuthCache, AuthState
from .client import ValidationResult, VibetoolClient
from .register_window import RegisterWindow


class LoginWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        client: VibetoolClient,
        cache: AuthCache,
        prefill_email: str = "",
    ):
        super().__init__(parent)
        self.title("Login VibeTool")
        self.geometry("440x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.client = client
        self.cache = cache
        self.success: bool = False
        self.last_attempt_email: str = prefill_email

        self._build_ui(prefill_email=prefill_email)

    # ---------- UI ----------

    def _build_ui(self, prefill_email: str) -> None:
        container = ttk.Frame(self, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Telegram Blaster",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 2))
        ttk.Label(
            container,
            text="By VibeTool.Club",
            font=("Segoe UI", 10),
            foreground="#64748b",
        ).pack(pady=(0, 16))

        ttk.Label(
            container,
            text="Login dengan akun member VibeTool.id",
            wraplength=380,
            justify="center",
            foreground="#475569",
        ).pack(pady=(0, 16))

        self.email_var = tk.StringVar(value=prefill_email)
        self.password_var = tk.StringVar()

        ttk.Label(container, text="Email").pack(anchor="w")
        self.email_entry = ttk.Entry(container, textvariable=self.email_var, width=40)
        self.email_entry.pack(fill="x", pady=(2, 10))

        ttk.Label(container, text="Password").pack(anchor="w")
        self.password_entry = ttk.Entry(container, textvariable=self.password_var, width=40, show="*")
        self.password_entry.pack(fill="x", pady=(2, 12))
        self.password_entry.bind("<Return>", lambda _e: self._on_login())

        self.status_label = ttk.Label(container, text="", wraplength=380, foreground="#dc2626")
        self.status_label.pack(fill="x", pady=(0, 8))

        self.login_btn = ttk.Button(container, text="Login", command=self._on_login)
        self.login_btn.pack(fill="x", pady=(2, 16))

        # --- Tombol pembantu di bawah ---
        register_row = ttk.Frame(container)
        register_row.pack(fill="x", pady=(0, 6))
        ttk.Button(register_row, text="Daftar di Sini", command=self._open_register_window).pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        ttk.Button(register_row, text="Daftar di Website", command=self._open_register_browser).pack(
            side="right", expand=True, fill="x", padx=(4, 0)
        )

        self.wa_btn = ttk.Button(
            container,
            text="Hubungi Admin via WhatsApp",
            command=self._open_admin_wa,
        )
        self.wa_btn.pack(fill="x")

        # Fokus awal ke field yang relevan.
        if prefill_email:
            self.password_entry.focus_set()
        else:
            self.email_entry.focus_set()

    # ---------- actions ----------

    def _on_login(self) -> None:
        email = self.email_var.get().strip().lower()
        password = self.password_var.get()
        if not email or not password:
            self._set_status("Email dan password wajib diisi.", error=True)
            return

        self._set_status("Memverifikasi ke vibetool.id…", error=False)
        self._set_busy(True)
        self.last_attempt_email = email

        def worker():
            result = self.client.validate_member(email=email, password=password)
            self.after(0, lambda: self._handle_login(result, email))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_login(self, result: ValidationResult, email: str) -> None:
        self._set_busy(False)

        if result.valid:
            user = result.user or {}
            state = AuthState.now(
                email=email,
                user_id=int(user.get("id") or 0),
                name=str(user.get("name") or ""),
            )
            try:
                self.cache.save(state)
            except Exception as e:  # noqa: BLE001
                # Cache gagal disimpan bukan blocker — user tetap bisa lanjut.
                self._set_status(f"Login OK, tapi cache gagal disimpan: {e}", error=False)
            self.success = True
            self.destroy()
            return

        self._set_status(result.message or "Login gagal.", error=True)

        if result.is_account_inactive:
            # User ada tapi belum aktif → arahkan ke tombol WA.
            messagebox.showinfo(
                "Akun Belum Aktif",
                "Akun ini terdaftar tapi belum diaktifkan admin.\n\n"
                "Klik tombol 'Hubungi Admin via WhatsApp' untuk minta aktivasi.",
                parent=self,
            )
        elif result.is_no_access:
            # User aktif tapi belum klaim produk teleblaster.
            self._prompt_claim_product()

    def _prompt_claim_product(self) -> None:
        from .config import VibetoolConfig  # local import untuk hindari circular

        cfg: VibetoolConfig = self.client.config
        url = f"{cfg.base_url.rstrip('/')}/dashboard/products"
        if messagebox.askyesno(
            "Belum Klaim Produk",
            "Akun kamu aktif, tapi belum klaim produk gratis Telegram Blaster\n"
            "di dashboard VibeTool.\n\n"
            "Buka halaman 'Produk' di vibetool.id untuk klaim sekarang?",
            parent=self,
        ):
            webbrowser.open(url)

    def _open_register_window(self) -> None:
        def on_register_success(email: str):
            self.email_var.set(email)
            self.password_var.set("")
            self.password_entry.focus_set()
            self._set_status(
                "Pendaftaran terkirim. Hubungi admin via WhatsApp untuk aktivasi, lalu login di sini.",
                error=False,
            )

        RegisterWindow(self, client=self.client, on_success_email=on_register_success)

    def _open_register_browser(self) -> None:
        webbrowser.open(self.client.config.web_register_url)

    def _open_admin_wa(self) -> None:
        admin = self.client.fetch_whatsapp_admin()
        if not admin.number:
            messagebox.showwarning(
                "Nomor Admin Belum Tersedia",
                admin.message or "Nomor admin belum dikonfigurasi.",
                parent=self,
            )
            return
        link = self.client.build_activation_wa_link(
            admin_number=admin.number,
            name="",
            email=self.last_attempt_email,
            whatsapp_number=None,
        )
        webbrowser.open(link)

    def _on_close(self) -> None:
        self.success = False
        self.destroy()

    # ---------- helpers ----------

    def _set_status(self, msg: str, *, error: bool) -> None:
        self.status_label.configure(text=msg, foreground="#dc2626" if error else "#475569")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.login_btn.configure(state=state, text="Memverifikasi…" if busy else "Login")
        self.email_entry.configure(state=state)
        self.password_entry.configure(state=state)
