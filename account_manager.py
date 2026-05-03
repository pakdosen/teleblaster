from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pyrogram_compat  # noqa: F401
from pyrogram import Client

from configs import Config
from crypto import decrypt_text
from utils import load_json, save_json_atomic


@dataclass
class SessionRecord:
    phone: str
    file_path: Path


class AccountManager:
    def __init__(self, config: Config):
        self.config = config
        self.cooldowns_path = Path(config.cooldowns_file)
        self.sessions_dir = Path(config.sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._rr_index = 0

    def _load_cooldowns(self) -> dict:
        data = load_json(str(self.cooldowns_path), default={})
        now = int(time.time())
        cleaned = {k: v for k, v in data.items() if int(v) > now}
        if cleaned != data:
            save_json_atomic(str(self.cooldowns_path), cleaned)
        return cleaned

    def _save_cooldowns(self, data: dict) -> None:
        save_json_atomic(str(self.cooldowns_path), data)

    def set_cooldown(self, phone: str, seconds: int) -> None:
        data = self._load_cooldowns()
        data[phone] = int(time.time()) + max(0, int(seconds))
        self._save_cooldowns(data)

    def get_cooldown_remaining(self, phone: str) -> int:
        data = self._load_cooldowns()
        ts = int(data.get(phone, 0))
        return max(0, ts - int(time.time()))

    def list_sessions(self) -> list[SessionRecord]:
        out = []
        for item in self.sessions_dir.glob("*.json"):
            phone = item.stem
            out.append(SessionRecord(phone=phone, file_path=item))
        return sorted(out, key=lambda x: x.phone)

    def remove_session(self, phone: str) -> bool:
        p = self.sessions_dir / f"{phone}.json"
        if p.exists():
            p.unlink()
            return True
        return False

    async def build_client(self, phone: str, password: str) -> Client:
        session_file = self.sessions_dir / f"{phone}.json"
        payload = load_json(str(session_file), default={})
        session_str = decrypt_text(payload["session"], password=password)
        return Client(
            name=f"acc_{phone}",
            api_id=self.config.api_id,
            api_hash=self.config.api_hash,
            session_string=session_str,
            in_memory=True,
        )

    def next_available_phones(self) -> list[str]:
        phones = [s.phone for s in self.list_sessions()]
        return [p for p in phones if self.get_cooldown_remaining(p) <= 0]

    def get_next_phone(self, exclude: set[str] | None = None) -> str | None:
        exclude = exclude or set()
        phones = self.next_available_phones()
        phones = [p for p in phones if p not in exclude]
        if not phones:
            return None

        idx = self._rr_index % len(phones)
        self._rr_index = (self._rr_index + 1) % len(phones)
        return phones[idx]

    def seconds_until_next_available(self) -> int:
        sessions = self.list_sessions()
        if not sessions:
            return 0
        remaining = [self.get_cooldown_remaining(s.phone) for s in sessions]
        positives = [x for x in remaining if x > 0]
        return min(positives) if positives else 0
