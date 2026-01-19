from __future__ import annotations

from typing import Any
from typing import Awaitable
from typing import Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from services.audio_service import AudioService
from services.speech.base import SpeechRecognizer
from utils.config import Settings


class ServicesMiddleware(BaseMiddleware):
    def __init__(
        self,
        *,
        settings: Settings,
        audio_service: AudioService,
        speech_recognizer: SpeechRecognizer,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._audio_service = audio_service
        self._speech_recognizer = speech_recognizer

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        data["settings"] = self._settings
        data["audio_service"] = self._audio_service
        data["speech_recognizer"] = self._speech_recognizer
        return await handler(event, data)

