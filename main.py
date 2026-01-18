import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.common import router as common_router
from utils.config import load_settings
from utils.logging_config import setup_logging


logger = logging.getLogger(__name__)


def _setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common_router)
    return dp


async def main() -> None:
    settings = load_settings()
    setup_logging(log_level=settings.log_level)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _setup_dispatcher()

    logger.info("Bot started (polling).")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

