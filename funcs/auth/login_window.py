"""Window login VibeTool yang muncul sebelum GUI utama Telegram Blaster.

UI didesain minimalis dengan 4 aksi utama: Login, Daftar di Sini (in-app),
Daftar di Website (browser), Hubungi Admin via WhatsApp. Hasil login
dikembalikan ke caller lewat callback `on_success`.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Optional

from .cache import AuthCache, AuthState
from .client import ValidationResult, VibetoolClient
from .register_window import RegisterWindow
from .theme import DARK_COLORS, apply_auth_theme, apply_window_icon, load_logo


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
        self.geometry("460x600")
        self.resizable(False, False)
        # Catatan: jangan panggil transient() kalau parent ter-withdraw,
        # karena di Windows itu bikin Toplevel ikut ke-hide & tidak muncul
        # di taskbar. Cek visibility parent dulu.
        try:
            if str(parent.state()) != "withdrawn":
                self.transient(parent)
        except Exception:
            pass
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        apply_auth_theme(self)
        apply_window_icon(self)

        self.client = client
        self.cache = cache
        self.success: bool = False
        self.last_attempt_email: str = prefill_email
        self._logo_ref = None  # cegah PhotoImage di-GC

        # Queue untuk komunikasi thread → main thread (Python 3.14+ tidak
        # mengizinkan tk.after() dipanggil dari thread lain). Setiap pesan
        # bentuknya: ("kind", payload, ...extra...).
        self._result_queue: "queue.Queue[tuple]" = queue.Queue()
        self._poll_after_id: Optional[str] = None

        self._build_ui(prefill_email=prefill_email)
        self._schedule_poll()

        # Paksa window muncul di depan & ambil fokus. Di Windows, Toplevel
        # kadang muncul di belakang console / window lain.
        self._force_to_front()

    def _force_to_front(self) -> None:
        try:
            self.update_idletasks()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self._unset_topmost())
            self.focus_force()
        except Exception:
            pass

    def _unset_topmost(self) -> None:
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass

    # ---------- UI ----------

    def _build_ui(self, prefill_email: str) -> None:
        container = ttk.Frame(self, padding=28, style="Auth.TFrame")
        container.pack(fill="both", expand=True)

        # --- Logo di header ---
        self._logo_ref = load_logo(72)
        if self._logo_ref is not None:
            logo_label = tk.Label(
                container,
                image=self._logo_ref,
                bg=DARK_COLORS["bg"],
                borderwidth=0,
                highlightthickness=0,
            )
            logo_label.pack(pady=(0, 8))

        ttk.Label(
            container,
            text="Telegram Blaster",
            style="AuthHeader.TLabel",
        ).pack(pady=(0, 2))
        ttk.Label(
            container,
            text="by VibeTool.Club",
            style="AuthSub.TLabel",
        ).pack(pady=(0, 16))

        ttk.Label(
            container,
            text="Login dengan akun member VibeTool.id",
            wraplength=380,
            justify="center",
            style="AuthSub.TLabel",
        ).pack(pady=(0, 18))

        self.email_var = tk.StringVar(value=prefill_email)
        self.password_var = tk.StringVar()

        ttk.Label(container, text="Email", style="Auth.TLabel").pack(anchor="w")
        self.email_entry = ttk.Entry(
            container,
            textvariable=self.email_var,
            width=40,
            style="Auth.TEntry",
        )
        self.email_entry.pack(fill="x", pady=(2, 10), ipady=4)

        ttk.Label(container, text="Password", style="Auth.TLabel").pack(anchor="w")
        self.password_entry = ttk.Entry(
            container,
            textvariable=self.password_var,
            width=40,
            show="*",
            style="Auth.TEntry",
        )
        self.password_entry.pack(fill="x", pady=(2, 12), ipady=4)
        self.password_entry.bind("<Return>", lambda _e: self._on_login())

        self.status_label = ttk.Label(
            container,
            text="",
            wraplength=380,
            style="AuthError.TLabel",
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        self.login_btn = ttk.Button(
            container,
            text="Login",
            command=self._on_login,
            style="AuthAccent.TButton",
        )
        self.login_btn.pack(fill="x", pady=(2, 16))

        # --- Tombol pembantu di bawah ---
        register_row = ttk.Frame(container, style="Auth.TFrame")
        register_row.pack(fill="x", pady=(0, 8))
        ttk.Button(
            register_row,
            text="Daftar di Sini",
            command=self._open_register_window,
            style="Auth.TButton",
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(
            register_row,
            text="Daftar di Website",
            command=self._open_register_browser,
            style="Auth.TButton",
        ).pack(side="right", expand=True, fill="x", padx=(4, 0))

        self.wa_btn = ttk.Button(
            container,
            text="Hubungi Admin via WhatsApp",
            command=self._open_admin_wa,
            style="Auth.TButton",
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

        q = self._result_queue

        def worker():
            # JANGAN panggil method Tk dari thread ini — cuma push ke queue.
            # Main loop akan polling queue via self.after().
            try:
                result = self.client.validate_member(email=email, password=password)
                q.put(("login_result", result, email))
            except BaseException as exc:  # noqa: BLE001
                q.put(("login_error", exc, email))

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
        elif result.error_code == "product_not_found":
            # Slug yang dikirim aplikasi tidak match dengan produk apapun
            # di vibetool.id. Kemungkinan besar admin pakai slug lain —
            # arahkan user untuk set VIBETOOL_PRODUCT_SLUG di .env.
            messagebox.showerror(
                "Produk Tidak Ditemukan",
                f"Aplikasi mencari produk dengan slug "
                f"'{self.client.config.product_slug}' di vibetool.id\n"
                "tapi produknya tidak ada.\n\n"
                "Cek halaman Admin → Products di vibetool.id, lalu salin slug\n"
                "produk Teleblaster ke file .env aplikasi:\n\n"
                "    VIBETOOL_PRODUCT_SLUG=<slug-produk-kamu>\n\n"
                "Lalu restart aplikasi.",
                parent=self,
            )

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
        # Fetch nomor admin di worker thread supaya UI tidak freeze. Hasilnya
        # akan diproses lewat queue di main loop (lihat _handle_wa_admin).
        self.wa_btn.configure(state="disabled", text="Mengambil nomor admin…")
        q = self._result_queue

        def worker():
            try:
                admin = self.client.fetch_whatsapp_admin()
                q.put(("wa_admin_result", admin))
            except BaseException as exc:  # noqa: BLE001
                q.put(("wa_admin_error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_wa_admin(self, admin) -> None:
        try:
            self.wa_btn.configure(state="normal", text="Hubungi Admin via WhatsApp")
        except Exception:
            pass
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

    # ---------- thread → main loop bridge ----------

    def _schedule_poll(self) -> None:
        try:
            self._poll_after_id = self.after(50, self._poll_result_queue)
        except Exception:
            self._poll_after_id = None

    def _poll_result_queue(self) -> None:
        # Drain semua pesan yang ada, lalu reschedule.
        try:
            while True:
                try:
                    msg = self._result_queue.get_nowait()
                except queue.Empty:
                    break
                self._dispatch(msg)
        finally:
            if self.winfo_exists():
                self._schedule_poll()

    def _dispatch(self, msg: tuple) -> None:
        kind = msg[0]
        try:
            if kind == "login_result":
                _, result, email = msg
                self._handle_login(result, email)
            elif kind == "login_error":
                _, exc, _email = msg
                self._set_busy(False)
                self._set_status(f"Error: {exc}", error=True)
            elif kind == "wa_admin_result":
                _, admin = msg
                self._handle_wa_admin(admin)
            elif kind == "wa_admin_error":
                _, exc = msg
                try:
                    self.wa_btn.configure(state="normal", text="Hubungi Admin via WhatsApp")
                except Exception:
                    pass
                messagebox.showwarning(
                    "Gagal Mengambil Nomor Admin",
                    f"Terjadi error saat fetch nomor admin: {exc}",
                    parent=self,
                )
        except Exception:
            # Jangan biarkan dispatch error bikin polling loop berhenti.
            pass

    def _on_close(self) -> None:
        self.success = False
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        self.destroy()

    # ---------- helpers ----------

    def _set_status(self, msg: str, *, error: bool) -> None:
        self.status_label.configure(
            text=msg,
            style="AuthError.TLabel" if error else "AuthMuted.TLabel",
        )

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.login_btn.configure(state=state, text="Memverifikasi…" if busy else "Login")
        self.email_entry.configure(state=state)
        self.password_entry.configure(state=state)
