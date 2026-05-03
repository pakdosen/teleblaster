import asyncio
import getpass
import re
from pathlib import Path

import pyrogram_compat  # noqa: F401
from pyrogram.enums import ParseMode
from rich.prompt import Confirm, Prompt

from account_manager import AccountManager
from configs import Config
from funcs.helpers import execute_with_rotation
from funcs.ui import error, info, success, warn
from utils import random_delay, read_members_csv, write_members_csv_atomic


MAX_LEN = 4096


def _md_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text, flags=re.DOTALL)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((https?://[^\s\)]+)\)", r"<a href=\"\2\">\1</a>", text)
    return text


def _ensure_template(path: str) -> None:
    p = Path(path)
    if not p.exists():
        p.write_text("# Hello\n\nPesan Anda di sini.", encoding="utf-8")


async def handle_broadcast(config: Config, manager: AccountManager) -> None:
    password = getpass.getpass("Encryption password: ")
    _ensure_template(config.template_file)
    msg_path = Prompt.ask("Path markdown file", default=config.template_file).strip()
    raw = Path(msg_path).read_text(encoding="utf-8")
    html = _md_to_html(raw)

    if len(html) > MAX_LEN:
        error("Message > 4096 chars setelah konversi")
        return

    info("Preview:")
    print(html)
    if not Confirm.ask("Kirim broadcast?", default=False):
        return

    rows = read_members_csv(config.members_csv)
    if not rows:
        warn("members.csv kosong")
        return

    done_ids: set[str] = set()
    sent = 0

    for row in rows:
        uid = row.get("ID", "")
        if not uid:
            continue

        try:
            async def _op(app, _phone: str):
                await app.send_message(int(uid), html, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                return True

            _, used_phone = await execute_with_rotation(manager, password, _op)
            sent += 1
            done_ids.add(uid)
            await asyncio.sleep(random_delay(30, 60))
            info(f"Sent to {uid} via {used_phone}")
        except RuntimeError as exc:
            error(str(exc))
            break
        except Exception:
            # Blocked/invalid users are removed to allow resume.
            done_ids.add(uid)

    if done_ids:
        left = [r for r in rows if r.get("ID", "") not in done_ids]
        write_members_csv_atomic(config.members_csv, left)
    success(f"Broadcast selesai, sent={sent}")
