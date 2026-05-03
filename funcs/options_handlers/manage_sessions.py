import getpass

import pyrogram_compat  # noqa: F401
from pyrogram.errors import RPCError
from rich.prompt import Confirm, Prompt
from rich.table import Table

from account_manager import AccountManager
from configs import Config
from funcs.ui import console, error, info, success, warn
from utils import mask_phone, normalize_menu_choice


async def handle_manage_sessions(config: Config, manager: AccountManager) -> None:
    info("01 - List All Sessions")
    info("02 - Test All Sessions")
    info("03 - Remove Inactive Sessions")
    info("00 - Back")
    choice = normalize_menu_choice(Prompt.ask("Choose", default="00"))

    if choice == "01":
        _list_sessions(manager)
    elif choice == "02":
        await _test_sessions(manager)
    elif choice == "03":
        await _remove_inactive(manager)


def _list_sessions(manager: AccountManager) -> None:
    table = Table(title="Sessions")
    table.add_column("Phone")
    table.add_column("Cooldown")
    sessions = manager.list_sessions()
    for sess in sessions:
        remain = manager.get_cooldown_remaining(sess.phone)
        table.add_row(mask_phone(sess.phone), f"{remain}s" if remain else "Active")
    console.print(table)


async def _test_sessions(manager: AccountManager) -> None:
    password = getpass.getpass("Encryption password: ")
    sessions = manager.list_sessions()
    if not sessions:
        warn("No sessions")
        return

    table = Table(title="Session Test")
    table.add_column("Phone")
    table.add_column("Result")

    for sess in sessions:
        try:
            app = await manager.build_client(sess.phone, password)
            await app.connect()
            me = await app.get_me()
            table.add_row(mask_phone(sess.phone), f"OK ({me.id})")
            await app.disconnect()
        except Exception as exc:
            table.add_row(mask_phone(sess.phone), f"FAILED ({exc})")

    console.print(table)


async def _remove_inactive(manager: AccountManager) -> None:
    password = getpass.getpass("Encryption password: ")
    sessions = manager.list_sessions()
    bad: list[str] = []
    for sess in sessions:
        try:
            app = await manager.build_client(sess.phone, password)
            await app.connect()
            await app.get_me()
            await app.disconnect()
        except Exception:
            bad.append(sess.phone)

    if not bad:
        success("Tidak ada session inactive")
        return

    warn("Inactive sessions: " + ", ".join(mask_phone(x) for x in bad))
    if Confirm.ask("Hapus semua inactive session?", default=False):
        for phone in bad:
            manager.remove_session(phone)
        success("Inactive sessions removed")
