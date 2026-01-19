from __future__ import annotations

import logging
from typing import Any
from typing import Awaitable
from typing import Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from storage.repositories import Repositories


logger = logging.getLogger(__name__)


class DbLoggingMiddleware(BaseMiddleware):
    def __init__(self, repos: Repositories) -> None:
        super().__init__()
        self._repos = repos

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        data["repos"] = self._repos

        if event.from_user is not None:
            user_id = event.from_user.id
            username = event.from_user.username
            try:
                await self._repos.upsert_user(user_id=user_id, username=username)
                await self._repos.log_message(
                    user_id=user_id,
                    direction="in",
                    msg_type=event.content_type,
                    text=event.text,
                    file_id=(event.voice.file_id if event.voice else None),
                )
            except Exception:
                logger.exception("Failed to log incoming message to DB")

        return await handler(event, data)

