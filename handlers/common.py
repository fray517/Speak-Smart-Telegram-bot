import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from storage.repositories import Repositories


logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    state: FSMContext,
    repos: Repositories,
) -> None:
    await state.clear()
    text = (
        "Привет! Я SpeakSmart.\n\n"
        "Доступные команды:\n"
        "/practice — голосовая практика\n"
        "/support — поддержка (FAQ/оператор)\n"
        "/help — помощь\n"
        "/cancel — отмена и сброс режима"
    )
    await message.answer(text)

    if message.from_user is not None:
        await repos.log_message(
            user_id=message.from_user.id,
            direction="out",
            msg_type="text",
            text=text,
        )


@router.message(Command("help"))
async def cmd_help(message: Message, repos: Repositories) -> None:
    text = (
        "Помощь:\n\n"
        "- /practice: бот пришлёт голосовую фразу, вы ответите голосом.\n"
        "- /support: задайте вопрос, бот попробует найти ответ в FAQ.\n"
        "- /cancel: выйти из текущего режима.\n"
    )
    await message.answer(text)

    if message.from_user is not None:
        await repos.log_message(
            user_id=message.from_user.id,
            direction="out",
            msg_type="text",
            text=text,
        )


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    repos: Repositories,
) -> None:
    current = await state.get_state()
    await state.clear()

    if current is None:
        text = "Ок. Вы не были в режиме — состояние чистое."
        await message.answer(text)

        if message.from_user is not None:
            await repos.log_message(
                user_id=message.from_user.id,
                direction="out",
                msg_type="text",
                text=text,
            )
        return

    text = "Ок. Режим отменён, состояние сброшено."
    await message.answer(text)

    if message.from_user is not None:
        await repos.log_message(
            user_id=message.from_user.id,
            direction="out",
            msg_type="text",
            text=text,
        )

