"""Regression test untuk bug Python 3.14: jangan panggil method Tk dari
worker thread. Tk strict thread-safety di 3.14 akan raise
`RuntimeError: main thread is not in main loop` kalau worker thread
panggil `widget.after()`, `widget.configure()`, dll.

Pendekatan test: panggil `_on_login()` / `_submit()`, pastikan worker
thread benar-benar jalan di thread terpisah dan HANYA push hasil ke
`_result_queue`. Tidak ada panggilan `after`/`configure` dari worker.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

try:
    import tkinter as tk  # noqa: F401
    _TK_AVAILABLE = True
except Exception:  # noqa: BLE001
    _TK_AVAILABLE = False


@unittest.skipUnless(_TK_AVAILABLE, "Tkinter not available")
@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "No display available")
class LoginWindowThreadingTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from funcs.auth import theme
        from funcs.auth.cache import AuthCache
        from funcs.auth.client import VibetoolClient
        from funcs.auth.config import VibetoolConfig

        # PhotoImage di-cache di module-level — kalau test ini bikin root
        # baru tiap setUp, cache dari root sebelumnya jadi stale. Reset.
        theme._logo_cache.clear()
        theme._styles_initialized.clear()

        self.root = tk.Tk()
        self.root.withdraw()
        self.tmpdir = tempfile.mkdtemp()
        self.cache = AuthCache(Path(self.tmpdir) / "auth.json")
        self.cfg = VibetoolConfig(base_url="https://example.com")
        self.client = VibetoolClient(self.cfg)
        self._main_tid = threading.get_ident()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _drain_event_loop(self, ms_total: int = 200) -> None:
        """Putar event loop sebentar supaya scheduled after() bisa fire."""
        deadline = time.time() + ms_total / 1000.0
        while time.time() < deadline:
            try:
                self.root.update_idletasks()
                self.root.update()
            except Exception:
                break
            time.sleep(0.01)

    def test_login_worker_runs_in_separate_thread_and_does_not_touch_tk(self):
        from funcs.auth.client import ValidationResult
        from funcs.auth.login_window import LoginWindow

        worker_thread_id = {}

        def fake_validate(email, password):
            worker_thread_id["tid"] = threading.get_ident()
            # Kalau Python 3.14 strict — panggil .after() dari sini akan
            # crash. Test ini ngecek bahwa client.validate_member dipanggil
            # dari thread non-main, lalu cek hasil pesan ada di queue
            # (artinya worker tidak crash karena Tk panggil dari thread).
            return ValidationResult(
                valid=False,
                error_code="invalid_credentials",
                http_status=401,
                message="Bad creds (mocked)",
            )

        win = LoginWindow(self.root, client=self.client, cache=self.cache, prefill_email="a@b.com")
        win.password_var.set("password123")

        with mock.patch.object(self.client, "validate_member", side_effect=fake_validate):
            win._on_login()
            # Tunggu worker selesai (max 1s)
            deadline = time.time() + 1.0
            while time.time() < deadline and "tid" not in worker_thread_id:
                time.sleep(0.01)

        # Worker harus jalan di thread non-main.
        self.assertIn("tid", worker_thread_id, "Worker harus benar-benar dipanggil")
        self.assertNotEqual(
            worker_thread_id["tid"],
            self._main_tid,
            "Worker harus jalan di thread terpisah (bukan main thread)",
        )

        # Hasil harus masuk ke queue (push dari worker, drain di main loop).
        msg = win._result_queue.get(timeout=1.0)
        self.assertEqual(msg[0], "login_result")
        result_obj = msg[1]
        self.assertFalse(result_obj.valid)
        self.assertEqual(result_obj.error_code, "invalid_credentials")

        # Manual dispatch dari main thread (simulasi polling loop).
        win._dispatch(msg)
        self._drain_event_loop(50)
        self.assertIn("Bad creds", win.status_label.cget("text"))

    def test_login_worker_exception_does_not_crash(self):
        """Kalau client raise exception, queue harus dapat 'login_error'."""
        from funcs.auth.login_window import LoginWindow

        win = LoginWindow(self.root, client=self.client, cache=self.cache)
        win.email_var.set("a@b.com")
        win.password_var.set("password123")

        with mock.patch.object(
            self.client,
            "validate_member",
            side_effect=RuntimeError("boom from worker"),
        ):
            win._on_login()
            msg = win._result_queue.get(timeout=1.0)

        self.assertEqual(msg[0], "login_error")
        self.assertIsInstance(msg[1], RuntimeError)
        self.assertEqual(str(msg[1]), "boom from worker")

        # Dispatch error → status label harus update, button kembali normal.
        win._dispatch(msg)
        self.assertIn("boom from worker", win.status_label.cget("text"))
        self.assertEqual(str(win.login_btn["state"]), "normal")

    def test_register_worker_runs_in_separate_thread(self):
        from funcs.auth.client import RegisterResult
        from funcs.auth.register_window import RegisterWindow

        win = RegisterWindow(self.root, client=self.client)
        win.name_var.set("Test User")
        win.email_var.set("test@example.com")
        win.wa_var.set("628123456789")
        win.password_var.set("password123")
        win.confirm_var.set("password123")

        worker_tid = {}

        def fake_register(**kwargs):
            worker_tid["tid"] = threading.get_ident()
            return RegisterResult(
                ok=False,
                error_code="validation_error",
                http_status=422,
                message="Email sudah terdaftar.",
                field_errors={"email": "sudah terdaftar"},
            )

        with mock.patch.object(self.client, "register", side_effect=fake_register):
            win._submit()
            deadline = time.time() + 1.0
            while time.time() < deadline and "tid" not in worker_tid:
                time.sleep(0.01)

        self.assertNotEqual(worker_tid.get("tid"), self._main_tid)
        msg = win._result_queue.get(timeout=1.0)
        self.assertEqual(msg[0], "register_result")
        self.assertEqual(msg[1].error_code, "validation_error")


if __name__ == "__main__":
    unittest.main()
