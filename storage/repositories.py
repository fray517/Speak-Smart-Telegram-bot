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

    async def get_open_ticket_by_user(self, *, user_id: int) -> int | None:
        row = await self.db.fetchone(
            """
            SELECT id
            FROM tickets
            WHERE user_id = ? AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """.strip(),
            (user_id,),
        )
        if row is None:
            return None
        return int(row["id"])

    async def create_ticket(self, *, user_id: int, last_user_message: str) -> int:
        now = _utc_now_iso()
        ticket_id = await self.db.execute_insert(
            """
            INSERT INTO tickets (user_id, status, created_at, updated_at, last_user_message)
            VALUES (?, 'open', ?, ?, ?)
            """.strip(),
            (user_id, now, now, last_user_message),
        )
        return ticket_id

    async def update_ticket_last_message(
        self,
        *,
        ticket_id: int,
        last_user_message: str,
    ) -> None:
        await self.db.execute(
            """
            UPDATE tickets
            SET last_user_message = ?, updated_at = ?
            WHERE id = ?
            """.strip(),
            (last_user_message, _utc_now_iso(), ticket_id),
        )
