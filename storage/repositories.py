from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from storage.db import Database


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Repositories:
    db: Database

    async def upsert_user(self, *, user_id: int, username: str | None) -> None:
        now = _utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO users (user_id, username, first_seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username
            """.strip(),
            (user_id, username, now),
        )

    async def log_message(
        self,
        *,
        user_id: int,
        direction: str,
        msg_type: str,
        text: str | None = None,
        file_id: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO messages (
                user_id, direction, msg_type, text, file_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """.strip(),
            (
                user_id,
                direction,
                msg_type,
                text,
                file_id,
                _utc_now_iso(),
            ),
        )

