from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    sessions_dir: str = "sessions"
    logs_dir: str = "logs"
    members_csv: str = "members.csv"
    cooldowns_file: str = "account_cooldowns.json"
    checkpoint_file: str = "scrape_checkpoint.json"
    template_file: str = "message_template.md"

    @classmethod
    def from_env(cls) -> "Config":
        api_id_raw = os.getenv("API_ID", "").strip()
        api_hash = os.getenv("API_HASH", "").strip()
        if not api_id_raw or not api_hash:
            raise ValueError("API_ID and API_HASH must be set in .env")
        return cls(api_id=int(api_id_raw), api_hash=api_hash)
