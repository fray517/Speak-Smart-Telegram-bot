from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final


DEFAULT_DB_PATH: Final[str] = "data/speaksMart.sqlite3"
DEFAULT_FAQ_PATH: Final[str] = "data/faq.json"
DEFAULT_PRACTICE_SETS_PATH: Final[str] = "assets/practice_sets.json"
DEFAULT_SPEECH_PROVIDER: Final[str] = "whisper"
DEFAULT_WHISPER_MODEL: Final[str] = "base"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"


def _parse_int(value: str, *, var_name: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError(f"{var_name} is empty")
    return int(value)


def _load_dotenv(path: Path) -> None:
    """
    Minimal .env loader.

    Supports lines like KEY=VALUE and ignores blank lines and comments (#...).
    Values are loaded only if the key is not already in the environment.
    """
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    operator_id: int
    db_path: str
    faq_path: str
    practice_sets_path: str
    speech_provider: str
    whisper_model: str
    ffmpeg_path: str
    log_level: str


def load_settings(*, dotenv_path: str = ".env") -> Settings:
    _load_dotenv(Path(dotenv_path))

    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    operator_id_raw = os.environ.get("OPERATOR_ID", "").strip()
    if not operator_id_raw:
        raise ValueError("OPERATOR_ID is required (one operator)")
    operator_id = _parse_int(operator_id_raw, var_name="OPERATOR_ID")

    ffmpeg_path = os.environ.get("FFMPEG_PATH", "").strip()
    if not ffmpeg_path:
        raise ValueError("FFMPEG_PATH is required (explicit path on Windows)")

    return Settings(
        bot_token=bot_token,
        operator_id=operator_id,
        db_path=os.environ.get("DB_PATH", DEFAULT_DB_PATH).strip(),
        faq_path=os.environ.get("FAQ_PATH", DEFAULT_FAQ_PATH).strip(),
        practice_sets_path=os.environ.get(
            "PRACTICE_SETS_PATH",
            DEFAULT_PRACTICE_SETS_PATH,
        ).strip(),
        speech_provider=os.environ.get(
            "SPEECH_PROVIDER",
            DEFAULT_SPEECH_PROVIDER,
        ).strip(),
        whisper_model=os.environ.get(
            "WHISPER_MODEL",
            DEFAULT_WHISPER_MODEL,
        ).strip(),
        ffmpeg_path=ffmpeg_path,
        log_level=os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip(),
    )

