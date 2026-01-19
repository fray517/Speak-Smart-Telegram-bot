import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.common import router as common_router
from handlers.operator import router as operator_router
from handlers.practice import router as practice_router
from handlers.support import router as support_router
from middlewares.db_logging import DbLoggingMiddleware
from middlewares.services import ServicesMiddleware
from services.audio_service import AudioService
from services.speech.factory import build_speech_recognizer
from storage.db import Database
from storage.repositories import Repositories
from utils.config import load_settings
from utils.logging_config import setup_logging


logger = logging.getLogger(__name__)


def _setup_dispatcher(
    *,
    repos: Repositories,
    audio_service: AudioService,
    speech_recognizer,
    settings,
) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common_router)
    dp.include_router(practice_router)
    dp.include_router(support_router)
    dp.include_router(operator_router)
    dp.message.middleware(DbLoggingMiddleware(repos))
    dp.message.middleware(
        ServicesMiddleware(
            settings=settings,
            audio_service=audio_service,
            speech_recognizer=speech_recognizer,
        )
    )
    return dp


async def main() -> None:
    settings = load_settings()
    setup_logging(log_level=settings.log_level)

    db = Database(db_path=settings.db_path)
    await db.init()
    repos = Repositories(db=db)

    audio_service = AudioService(ffmpeg_path=settings.ffmpeg_path)
    speech_recognizer = build_speech_recognizer(
        provider=settings.speech_provider,
        whisper_model=settings.whisper_model,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _setup_dispatcher(
        repos=repos,
        audio_service=audio_service,
        speech_recognizer=speech_recognizer,
        settings=settings,
    )

    logger.info("Bot started (polling).")
    try:
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Stop signal received. Stopping bot...")
    finally:
        await bot.session.close()
        await db.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

