import asyncio
import base64
import time
from pathlib import Path
from typing import Callable

import qrcode
from pyrogram.raw import functions, types
from pyrogram.session import Auth, Session


def _print_qr(url: str) -> None:
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    print("\nScan QR ini dari Telegram mobile: Settings > Devices > Link Desktop Device\n")
    for row in matrix:
        line = "".join("██" if cell else "  " for cell in row)
        print(line)
    print(f"\nURL: {url}\n")


def _save_qr_png(url: str, out_path: str = "qr_login.png") -> None:
    img = qrcode.make(url)
    img.save(out_path)
    print(f"QR image saved: {Path(out_path).resolve()}")


async def show_qr_and_wait_login(
    app,
    api_id: int,
    api_hash: str,
    timeout_seconds: int = 120,
    out_path: str = "qr_login.png",
    on_qr_file: Callable[[str, str], None] | None = None,
    on_event: Callable[[str], None] | None = None,
) -> bool:
    deadline = time.time() + timeout_seconds
    token: bytes | None = None
    last_shown_token: bytes | None = None

    def _emit(msg: str) -> None:
        if on_event is not None:
            try:
                on_event(msg)
            except Exception:
                pass

    def _token_to_url(token_bytes: bytes) -> str:
        token_b64 = base64.urlsafe_b64encode(token_bytes).decode("ascii").rstrip("=")
        return f"tg://login?token={token_b64}"

    async def _switch_dc(dc_id: int) -> None:
        await app.session.stop()
        await app.storage.dc_id(dc_id)
        await app.storage.auth_key(
            await Auth(app, await app.storage.dc_id(), await app.storage.test_mode()).create()
        )
        app.session = Session(
            app,
            await app.storage.dc_id(),
            await app.storage.auth_key(),
            await app.storage.test_mode(),
        )
        await app.session.start()

    async def _apply_authorization(auth_obj, note: str) -> bool:
        user = getattr(auth_obj, "user", None)
        if user is None:
            return False
        await app.storage.user_id(user.id)
        await app.storage.is_bot(bool(getattr(user, "bot", False)))
        await app.storage.save()
        _emit(f"QR: authorization tersimpan ({note})")
        return True

    async def _export_and_show_token() -> bool:
        nonlocal token, last_shown_token

        _emit("QR: export login token")
        token_obj = await app.invoke(
            functions.auth.ExportLoginToken(
                api_id=api_id,
                api_hash=api_hash,
                except_ids=[],
            )
        )

        if isinstance(token_obj, types.auth.LoginTokenMigrateTo):
            _emit(f"QR: export migrate to DC {token_obj.dc_id}")
            await _switch_dc(token_obj.dc_id)
            token_obj = await app.invoke(
                functions.auth.ExportLoginToken(
                    api_id=api_id,
                    api_hash=api_hash,
                    except_ids=[],
                )
            )

        if isinstance(token_obj, types.auth.LoginTokenSuccess):
            return await _apply_authorization(token_obj.authorization, "success saat export")

        if not isinstance(token_obj, types.auth.LoginToken):
            _emit("QR: export tidak mengembalikan LoginToken")
            return False

        token = token_obj.token
        if token != last_shown_token:
            url = _token_to_url(token)
            _save_qr_png(url, out_path=out_path)
            if on_qr_file is not None:
                try:
                    on_qr_file(str(Path(out_path).resolve()), url)
                except Exception:
                    pass
            _print_qr(url)
            last_shown_token = token

        _emit("QR: token siap, menunggu scan")
        return False

    immediate_ok = await _export_and_show_token()
    if immediate_ok:
        return True
    if not token:
        return False

    # Poll auth.exportLoginToken to detect when the user accepts the QR on a primary device.
    # Per https://core.telegram.org/api/qr-login the secondary device polls exportLoginToken
    # (NOT importLoginToken) until the server returns auth.loginTokenSuccess.
    while time.time() < deadline:
        try:
            uid = await app.storage.user_id()
            if uid and int(uid) > 0:
                _emit("QR: authorization terdeteksi via storage")
                return True
        except Exception:
            pass

        try:
            me = await app.get_me()
            if me and getattr(me, "id", None):
                _emit("QR: authorization terdeteksi via get_me")
                return True
        except Exception:
            pass

        try:
            ok = await _export_and_show_token()
        except Exception as exc:
            _emit(f"QR: poll error {type(exc).__name__}: {exc}")
            await asyncio.sleep(1)
            continue

        if ok:
            return True
        if not token:
            return False

        await asyncio.sleep(2)

    try:
        uid = await app.storage.user_id()
        if uid and int(uid) > 0:
            return True
    except Exception:
        pass

    try:
        me = await app.get_me()
        if me and getattr(me, "id", None):
            return True
    except Exception:
        pass

    return False
