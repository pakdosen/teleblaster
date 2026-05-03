import asyncio
import getpass

import pyrogram_compat  # noqa: F401
from rich.prompt import Prompt

from account_manager import AccountManager
from configs import Config
from funcs.helpers import execute_with_rotation
from funcs.ui import error, info, success, warn
from utils import normalize_menu_choice, random_delay, read_members_csv, write_members_csv_atomic


async def handle_add_members(config: Config, manager: AccountManager) -> None:
    info("01 - Rush Adder (remove processed from CSV)")
    info("02 - Calm Adder (keep CSV)")
    info("00 - Back")
    choice = normalize_menu_choice(Prompt.ask("Choose", default="00"))
    if choice not in {"01", "02"}:
        return

    rush_mode = choice == "01"
    password = getpass.getpass("Encryption password: ")
    target = Prompt.ask("Target group username/link").strip()

    rows = read_members_csv(config.members_csv)
    if not rows:
        warn("members.csv kosong")
        return

    processed_ids: set[str] = set()
    added = 0
    skipped = 0

    for row in rows:
        uid = row.get("ID", "").strip()
        if not uid:
            skipped += 1
            continue

        try:
            async def _op(app, _phone: str):
                await app.add_chat_members(target, int(uid))
                return True

            _, used_phone = await execute_with_rotation(manager, password, _op)
            added += 1
            processed_ids.add(uid)
            await asyncio.sleep(random_delay(3, 8))
            info(f"Added {uid} via {used_phone}")
        except Exception:
            skipped += 1
            processed_ids.add(uid)

    if rush_mode and processed_ids:
        remaining = [r for r in rows if r.get("ID", "") not in processed_ids]
        write_members_csv_atomic(config.members_csv, remaining)

    success(f"Adder selesai: added={added}, skipped={skipped}")
