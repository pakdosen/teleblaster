import asyncio
import getpass

import pyrogram_compat  # noqa: F401
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded

from configs import Config
from funcs.qr_auth import show_qr_and_wait_login


async def main() -> None:
    config = Config.from_env()
    app = Client(
        name="qr_quick_test",
        api_id=config.api_id,
        api_hash=config.api_hash,
        in_memory=True,
    )

    try:
        await app.connect()
        ok = await show_qr_and_wait_login(app, config.api_id, config.api_hash, timeout_seconds=120)
        if not ok:
            print("[FAILED] QR login timeout atau token invalid")
            return

        try:
            me = await app.get_me()
        except SessionPasswordNeeded:
            pw = getpass.getpass("Masukkan 2FA password: ")
            await app.check_password(pw)
            me = await app.get_me()

        print("[OK] QR login berhasil")
        print(f"User ID: {me.id}")
        print(f"Phone: +{me.phone_number}" if me.phone_number else "Phone: <none>")
        print(f"Username: @{me.username}" if me.username else "Username: <none>")
    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
