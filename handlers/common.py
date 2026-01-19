import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import ReplyKeyboardRemove

from storage.repositories import Repositories
from utils.config import Settings


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
        await message.answer(text, reply_markup=ReplyKeyboardRemove())

        if message.from_user is not None:
            await repos.log_message(
                user_id=message.from_user.id,
                direction="out",
                msg_type="text",
                text=text,
            )
        return

    text = "Ок. Режим отменён, состояние сброшено."
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

    if message.from_user is not None:
        await repos.log_message(
            user_id=message.from_user.id,
            direction="out",
            msg_type="text",
            text=text,
        )


@router.message(Command("myid"))
async def cmd_myid(message: Message, settings: Settings) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    await message.answer(
        "Идентификаторы:\n\n"
        f"user_id: {user_id}\n"
        f"chat_id: {chat_id}\n\n"
        f"OPERATOR_ID (из .env): {settings.operator_id}"
    )


@router.message(Command("ping_operator"))
async def cmd_ping_operator(message: Message, settings: Settings) -> None:
    """
    Диагностика: проверяем, может ли бот отправить сообщение оператору.
    """
    try:
        sent = await message.bot.send_message(
            settings.operator_id,
            "Проверка связи: это тестовое сообщение оператору.",
        )
    except Exception as exc:
        logger.exception("Failed to ping operator")
        await message.answer(f"Не получилось отправить оператору: {exc}")
        return

    await message.answer(
        "Ок, сообщение оператору отправлено.\n"
        f"message_id: {sent.message_id}"
    )

