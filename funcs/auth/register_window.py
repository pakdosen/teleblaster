"""Window registrasi member VibeTool di dalam aplikasi (Tkinter Toplevel).

Form mengikuti field yang ada di https://vibetool.id/register :
Name, Email, Nomor WhatsApp, Password, Confirm Password.

Submit ke endpoint JSON `POST /api/auth/register`. Pada sukses, window
menampilkan layar "Registrasi Berhasil" dengan tombol "Hubungi Admin via
WhatsApp" (sama dengan halaman /pending di website).
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Optional

from .client import VibetoolClient
from .theme import DARK_COLORS, apply_auth_theme, apply_window_icon, load_logo


class RegisterWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, client: VibetoolClient, on_success_email: Optional[callable] = None):
        super().__init__(parent)
        self.title("Daftar Akun VibeTool")
        self.geometry("480x640")
        self.resizable(False, False)
        # Sama seperti LoginWindow: jangan transient() ke parent yang
        # ter-withdraw — di Windows itu bikin window hidden.
        try:
            if str(parent.state()) != "withdrawn":
                self.transient(parent)
        except Exception:
            pass
        self.grab_set()

        apply_auth_theme(self)
        apply_window_icon(self)

        self.client = client
        self.on_success_email = on_success_email
        self.registered_user: Optional[dict] = None
        self._logo_ref = None  # cegah PhotoImage di-GC

        self._build_form()

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

    # ---------- form ----------

    def _build_form(self) -> None:
        container = ttk.Frame(self, padding=24, style="Auth.TFrame")
        container.pack(fill="both", expand=True)

        # Logo kecil di header
        self._logo_ref = load_logo(56)
        if self._logo_ref is not None:
            tk.Label(
                container,
                image=self._logo_ref,
                bg=DARK_COLORS["bg"],
                borderwidth=0,
                highlightthickness=0,
            ).pack(pady=(0, 4))

        ttk.Label(
            container,
            text="Daftar Akun VibeTool",
            style="AuthHeader.TLabel",
        ).pack(pady=(0, 4))
        ttk.Label(
            container,
            text="Setelah daftar, akun perlu diaktifkan admin via WhatsApp.",
            wraplength=400,
            justify="center",
            style="AuthSub.TLabel",
        ).pack(pady=(0, 16))

        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.wa_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()

        for label, var, show in (
            ("Nama", self.name_var, None),
            ("Email", self.email_var, None),
            ("Nomor WhatsApp", self.wa_var, None),
            ("Password", self.password_var, "*"),
            ("Konfirmasi Password", self.confirm_var, "*"),
        ):
            ttk.Label(container, text=label, style="Auth.TLabel").pack(anchor="w")
            entry = ttk.Entry(
                container,
                textvariable=var,
                width=40,
                show=show if show else "",
                style="Auth.TEntry",
            )
            entry.pack(fill="x", pady=(2, 10), ipady=3)

        self.status_label = ttk.Label(
            container,
            text="",
            wraplength=400,
            style="AuthError.TLabel",
        )
        self.status_label.pack(fill="x", pady=(0, 8))

        button_row = ttk.Frame(container, style="Auth.TFrame")
        button_row.pack(fill="x", pady=(8, 0))

        self.submit_btn = ttk.Button(
            button_row,
            text="Daftar",
            command=self._submit,
            style="AuthAccent.TButton",
        )
        self.submit_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        ttk.Button(
            button_row,
            text="Tutup",
            command=self.destroy,
            style="Auth.TButton",
        ).pack(side="right", expand=True, fill="x", padx=(4, 0))

    # ---------- submit ----------

    def _submit(self) -> None:
        name = self.name_var.get().strip()
        email = self.email_var.get().strip().lower()
        wa = self.wa_var.get().strip()
        password = self.password_var.get()
        confirm = self.confirm_var.get()

        if not name or not email or not password or not confirm:
            self._set_error("Semua field wajib diisi (kecuali WhatsApp opsional).")
            return
        if password != confirm:
            self._set_error("Password dan konfirmasi tidak sama.")
            return
        if len(password) < 8:
            self._set_error("Password minimal 8 karakter.")
            return

        self._set_error("")
        self.submit_btn.configure(state="disabled", text="Mengirim...")

        def worker():
            result = self.client.register(
                name=name,
                email=email,
                whatsapp_number=wa,
                password=password,
                password_confirmation=confirm,
            )
            self.after(0, lambda: self._handle_result(result, email))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, result, email: str) -> None:
        self.submit_btn.configure(state="normal", text="Daftar")

        if result.ok:
            self.registered_user = result.user or {"email": email}
            if self.on_success_email:
                try:
                    self.on_success_email(email)
                except Exception:
                    pass
            self._render_success(result)
            return

        if result.error_code == "validation_error" and result.field_errors:
            lines = [f"• {self._field_label(k)}: {v}" for k, v in result.field_errors.items()]
            self._set_error(result.message + "\n" + "\n".join(lines))
            return

        self._set_error(result.message or "Registrasi gagal.")

    def _set_error(self, msg: str) -> None:
        self.status_label.configure(text=msg)

    def _field_label(self, field: str) -> str:
        return {
            "name": "Nama",
            "email": "Email",
            "whatsapp_number": "Nomor WhatsApp",
            "password": "Password",
        }.get(field, field)

    # ---------- success view ----------

    def _render_success(self, result) -> None:
        for child in self.winfo_children():
            child.destroy()

        container = ttk.Frame(self, padding=24, style="Auth.TFrame")
        container.pack(fill="both", expand=True)

        # Logo header sukses juga
        self._logo_ref = load_logo(64)
        if self._logo_ref is not None:
            tk.Label(
                container,
                image=self._logo_ref,
                bg=DARK_COLORS["bg"],
                borderwidth=0,
                highlightthickness=0,
            ).pack(pady=(8, 4))

        ttk.Label(
            container,
            text="Registrasi Berhasil!",
            style="AuthOk.TLabel",
            font=("Segoe UI Semibold", 18),
        ).pack(pady=(0, 12))
        ttk.Label(
            container,
            text=(
                "Akun kamu sedang menunggu aktivasi oleh admin.\n"
                "Klik tombol di bawah untuk menghubungi admin via WhatsApp\n"
                "dan minta aktivasi akun kamu."
            ),
            justify="center",
            wraplength=400,
            style="AuthSub.TLabel",
        ).pack(pady=(0, 16))

        if result.user:
            # ttk.LabelFrame susah di-style sepenuhnya — pakai tk.Frame manual
            # dengan border halus untuk konsistensi tema gelap.
            info_box = tk.Frame(
                container,
                bg=DARK_COLORS["panel"],
                highlightbackground=DARK_COLORS["border"],
                highlightthickness=1,
            )
            info_box.pack(fill="x", pady=(0, 16))
            heading = tk.Label(
                info_box,
                text="Data Pendaftaran",
                bg=DARK_COLORS["panel"],
                fg=DARK_COLORS["muted"],
                font=("Segoe UI", 9),
            )
            heading.pack(anchor="w", padx=12, pady=(8, 4))
            for line in (
                f"Nama: {result.user.get('name', '-')}",
                f"Email: {result.user.get('email', '-')}",
                f"No WA: {result.user.get('whatsapp_number', '-') or '-'}",
            ):
                tk.Label(
                    info_box,
                    text=line,
                    bg=DARK_COLORS["panel"],
                    fg=DARK_COLORS["text"],
                    font=("Segoe UI", 10),
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=1, fill="x")
            tk.Frame(info_box, height=8, bg=DARK_COLORS["panel"]).pack()

        ttk.Button(
            container,
            text="Hubungi Admin via WhatsApp",
            command=self._open_admin_wa,
            style="AuthOk.TButton",
        ).pack(fill="x", pady=(0, 8))
        ttk.Button(
            container,
            text="Sudah Diaktifkan? Tutup & Login",
            command=self.destroy,
            style="Auth.TButton",
        ).pack(fill="x")

    def _open_admin_wa(self) -> None:
        admin = self.client.fetch_whatsapp_admin()
        if not admin.number:
            messagebox.showwarning(
                "Nomor Admin Belum Tersedia",
                admin.message or "Nomor admin belum dikonfigurasi.",
                parent=self,
            )
            return
        user = self.registered_user or {}
        link = self.client.build_activation_wa_link(
            admin_number=admin.number,
            name=user.get("name", ""),
            email=user.get("email", ""),
            whatsapp_number=user.get("whatsapp_number"),
        )
        webbrowser.open(link)
