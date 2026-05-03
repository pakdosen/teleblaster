import getpass
from pathlib import Path

import pyrogram_compat  # noqa: F401
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from rich.prompt import Prompt

from configs import Config
from funcs.helpers import save_session_string
from funcs.qr_auth import show_qr_and_wait_login
from funcs.ui import error, info, success, warn
from utils import is_valid_phone, normalize_menu_choice


async def handle_login(config: Config) -> None:
    info("01 - Login with Phone Number")
    info("02 - Login with QR Code")
    info("03 - Login from TData (best effort)")
    info("00 - Back")
    choice = normalize_menu_choice(Prompt.ask("Choose", default="00"))

    if choice == "01":
        await _login_phone(config)
    elif choice == "02":
        await _login_qr(config)
    elif choice == "03":
        await _login_tdata_best_effort(config)
    elif choice == "00":
        return
    else:
        error("Invalid option")


async def _login_phone(config: Config) -> None:
    phone = Prompt.ask("Phone (+628...)").strip()
    if not is_valid_phone(phone):
        error("Phone format invalid")
        return

    password = getpass.getpass("Buat/masukkan encryption password: ").strip()
    if len(password) < 4:
        error("Password minimal 4 karakter")
        return

    app = Client(
        name=f"login_{phone}",
        api_id=config.api_id,
        api_hash=config.api_hash,
        in_memory=True,
    )

    try:
        await app.connect()
        sent = await app.send_code(phone)
        otp = Prompt.ask("OTP code").replace(" ", "")
        try:
            await app.sign_in(phone_number=phone, phone_code_hash=sent.phone_code_hash, phone_code=otp)
        except SessionPasswordNeeded:
            twofa = getpass.getpass("2FA password: ")
            await app.check_password(twofa)

        sess = await app.export_session_string()
        await save_session_string(config=config, phone=phone, session_string=sess, password=password)
        success("Session tersimpan terenkripsi")
    except Exception as exc:
        error(f"Login gagal: {exc}")
    finally:
        await app.disconnect()


async def _login_qr(config: Config) -> None:
    phone_label = Prompt.ask("Label phone untuk session (contoh +628123...)").strip()
    if not is_valid_phone(phone_label):
        error("Phone format invalid")
        return

    password = getpass.getpass("Buat/masukkan encryption password: ").strip()
    if len(password) < 4:
        error("Password minimal 4 karakter")
        return

    app = Client(
        name=f"login_qr_{phone_label}",
        api_id=config.api_id,
        api_hash=config.api_hash,
        in_memory=True,
    )

    try:
        await app.connect()
        info("Menunggu scan QR hingga 2 menit...")
        authed = await show_qr_and_wait_login(app, config.api_id, config.api_hash, timeout_seconds=120)

        if not authed:
            error("QR login timeout, coba ulangi")
            return

        try:
            me = await app.get_me()
            if me.phone_number:
                phone_label = f"+{me.phone_number}"
        except Exception:
            pass

        sess = await app.export_session_string()
        await save_session_string(config=config, phone=phone_label, session_string=sess, password=password)
        success("QR login sukses, session tersimpan terenkripsi")
    except SessionPasswordNeeded:
        twofa = getpass.getpass("2FA password: ")
        try:
            await app.check_password(twofa)
            sess = await app.export_session_string()
            await save_session_string(config=config, phone=phone_label, session_string=sess, password=password)
            success("QR login + 2FA sukses, session tersimpan")
        except Exception as exc:
            error(f"2FA gagal: {exc}")
    except Exception as exc:
        error(f"QR login gagal: {exc}")
    finally:
        await app.disconnect()


async def _login_tdata_best_effort(config: Config) -> None:
    info("Mode best-effort: TData direct conversion ke Pyrogram belum stabil lintas versi Telegram Desktop.")
    info("Fallback aman: pakai converter eksternal lalu import session string Pyrogram.")

    tdata_path = Prompt.ask("Path folder tdata (opsional, untuk validasi)", default="").strip()
    if tdata_path:
        p = Path(tdata_path)
        if not p.exists() or not p.is_dir():
            error("Path tdata tidak valid")
            return
        info("Folder tdata terdeteksi")

    phone = Prompt.ask("Phone untuk nama session (+628...)").strip()
    if not is_valid_phone(phone):
        error("Phone format invalid")
        return

    password = getpass.getpass("Buat/masukkan encryption password: ").strip()
    if len(password) < 4:
        error("Password minimal 4 karakter")
        return

    session_string = Prompt.ask("Paste Pyrogram session string hasil converter").strip()
    if len(session_string) < 20:
        error("Session string tampak tidak valid")
        return

    await save_session_string(config=config, phone=phone, session_string=session_string, password=password)
    success("Session hasil import tersimpan terenkripsi")
