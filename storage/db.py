from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass(slots=True)
class Database:
    db_path: str
    migrations_path: str = "storage/migrations.sql"
    _conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._conn is not None:
            return

        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

    async def init(self) -> None:
        await self.connect()
        assert self._conn is not None

        sql = Path(self.migrations_path).read_text(encoding="utf-8")
        await self._conn.executescript(sql)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is None:
            return
        await self._conn.close()
        self._conn = None

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        assert self._conn is not None
        await self._conn.execute(query, params)
        await self._conn.commit()

    async def fetchone(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> aiosqlite.Row | None:
        assert self._conn is not None
        async with self._conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[aiosqlite.Row]:
        assert self._conn is not None
        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return list(rows)

