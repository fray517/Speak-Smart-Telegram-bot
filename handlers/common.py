import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я SpeakSmart.\n\n"
        "Доступные команды:\n"
        "/practice — голосовая практика\n"
        "/support — поддержка (FAQ/оператор)\n"
        "/help — помощь\n"
        "/cancel — отмена и сброс режима"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Помощь:\n\n"
        "- /practice: бот пришлёт голосовую фразу, вы ответите голосом.\n"
        "- /support: задайте вопрос, бот попробует найти ответ в FAQ.\n"
        "- /cancel: выйти из текущего режима.\n"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()

    if current is None:
        await message.answer("Ок. Вы не были в режиме — состояние чистое.")
        return

    await message.answer("Ок. Режим отменён, состояние сброшено.")

