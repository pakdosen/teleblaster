import csv
import json
import random
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse


MEMBER_HEADERS = ["Name", "ID", "Username", "Access Hash", "Group Name", "Group ID"]

SCRAPE_RESULTS_DIR = "Hasil Scrape Member"

_FS_INVALID_CHARS = set('<>:"/\\|?*')
_WINDOWS_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def sanitize_filename(name: str, max_len: int = 100, fallback: str = "untitled") -> str:
    """Return a filesystem-safe version of `name` suitable for cross-platform filenames.

    Replaces characters illegal on Windows (`<>:"/\\|?*`) and control chars (ord < 32)
    with underscores, trims surrounding whitespace and trailing dots, avoids reserved
    Windows device names (CON, PRN, COM1, etc.), and truncates to `max_len` chars.
    Returns `fallback` if the result would otherwise be empty.
    """
    cleaned = "".join(
        "_" if (c in _FS_INVALID_CHARS or ord(c) < 32) else c
        for c in (name or "")
    ).strip().rstrip(". ").strip()

    if cleaned.upper().split(".", 1)[0] in _WINDOWS_RESERVED_NAMES:
        cleaned = "_" + cleaned

    if not cleaned:
        return fallback

    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(". ").strip() or fallback

    return cleaned


def per_group_members_path(members_csv_path: str, group_title: str) -> Path:
    """Build the path for a per-group scrape CSV next to `members_csv_path`.

    Result: `<members_csv parent>/Hasil Scrape Member/<sanitized title>.csv`.
    """
    csv_path = Path(members_csv_path)
    base_dir = csv_path.parent if str(csv_path.parent) not in ("", ".") else Path(".")
    safe = sanitize_filename(group_title)
    return base_dir / SCRAPE_RESULTS_DIR / f"{safe}.csv"


def ensure_paths(*paths: str) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return "***"
    return f"{phone[:5]}***{phone[-3:]}"


def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"\+?[1-9]\d{6,14}", phone.strip()))


def load_json(path: str, default):
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path: str, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(p.parent)) as tf:
        json.dump(data, tf, indent=2, ensure_ascii=True)
        temp_name = tf.name
    Path(temp_name).replace(p)


def read_members_csv(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_members_csv_atomic(path: str, rows: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="", dir=str(p.parent)) as tf:
        writer = csv.DictWriter(tf, fieldnames=MEMBER_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        temp_name = tf.name
    Path(temp_name).replace(p)


def append_members_dedup(path: str, rows: list[dict]) -> tuple[int, int]:
    existing = read_members_csv(path)
    seen = {row.get("ID", "") for row in existing}
    before = len(existing)
    for row in rows:
        rid = str(row.get("ID", ""))
        if rid and rid not in seen:
            existing.append(row)
            seen.add(rid)
    write_members_csv_atomic(path, existing)
    return before, len(existing)


def random_delay(low: int, high: int) -> float:
    return random.uniform(low, high)


def normalize_menu_choice(raw: str) -> str:
    value = (raw or "").strip()
    if value.isdigit() and len(value) < 2:
        return value.zfill(2)
    return value


def normalize_chat_target(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""

    # Preserve raw numeric chat IDs such as -100xxxxxxxxxx.
    if re.fullmatch(r"-?\d+", value):
        return value

    if value.startswith("@"):
        return value[1:]

    if value.startswith("t.me/"):
        value = "https://" + value

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        host = (parsed.netloc or "").lower()
        if host.endswith("t.me") or host.endswith("telegram.me"):
            path = (parsed.path or "").lstrip("/")
            if not path:
                return ""
            if path.startswith("joinchat/"):
                path = path.split("/", 1)[1]
                return "+" + path if path else ""
            return path.split("/", 1)[0]

    return value
