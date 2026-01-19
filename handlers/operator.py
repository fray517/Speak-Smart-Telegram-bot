import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import Message

from storage.repositories import Repositories
from utils.config import Settings


logger = logging.getLogger(__name__)

router = Router()

CB_CLOSE_PREFIX = "close_ticket:"


def _parse_close_ticket_id(text: str) -> int | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[1].strip().lstrip("#"))
    except ValueError:
        return None


def _parse_close_ticket_callback(data: str | None) -> int | None:
    if not data:
        return None
    if not data.startswith(CB_CLOSE_PREFIX):
        return None
    try:
        return int(data.removeprefix(CB_CLOSE_PREFIX))
    except ValueError:
        return None


@router.message(Command("close"))
async def cmd_close(
    message: Message,
    repos: Repositories,
    settings: Settings,
) -> None:
    if message.from_user is None or message.from_user.id != settings.operator_id:
        return

    ticket_id = _parse_close_ticket_id(message.text or "")
    if ticket_id is None:
        await message.answer("Использование: /close <ticket_id>")
        return

    ok = await repos.close_ticket(ticket_id=ticket_id)
    if not ok:
        await message.answer(f"Не нашёл тикет #{ticket_id}.")
        return

    user_id = await repos.get_ticket_user_id(ticket_id=ticket_id)
    if user_id is not None:
        await message.bot.send_message(
            user_id,
            f"Тикет #{ticket_id} закрыт оператором. Если нужна помощь — /support.",
        )
        await repos.log_message(
            user_id=user_id,
            direction="out",
            msg_type="text",
            text=f"ticket_closed:{ticket_id}",
        )

    await message.answer(f"Ок. Тикет #{ticket_id} закрыт.")


@router.callback_query()
async def on_operator_callback(
    callback: CallbackQuery,
    repos: Repositories,
    settings: Settings,
) -> None:
    if callback.from_user.id != settings.operator_id:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    ticket_id = _parse_close_ticket_callback(callback.data)
    if ticket_id is None:
        await callback.answer()
        return

    ok = await repos.close_ticket(ticket_id=ticket_id)
    if not ok:
        await callback.answer("Тикет не найден.", show_alert=True)
        return

    user_id = await repos.get_ticket_user_id(ticket_id=ticket_id)
    if user_id is not None:
        await callback.bot.send_message(
            user_id,
            f"Тикет #{ticket_id} закрыт оператором. Если нужна помощь — /support.",
            parse_mode=None,
        )
        await repos.log_message(
            user_id=user_id,
            direction="out",
            msg_type="text",
            text=f"ticket_closed:{ticket_id}",
        )

    await callback.answer(f"Тикет #{ticket_id} закрыт.")
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.exception("Failed to edit operator message markup")


@router.message()
async def on_operator_message(
    message: Message,
    repos: Repositories,
    settings: Settings,
) -> None:
    if message.from_user is None or message.from_user.id != settings.operator_id:
        return

    if message.reply_to_message is None:
        await message.answer(
            "Ответьте reply на сообщение пользователя (которое прислал бот), "
            "чтобы я понял, кому переслать ответ.\n\n"
            "Либо используйте /close 123 (где 123 — номер тикета)."
        )
        return

    replied_id = message.reply_to_message.message_id
    user_id = await repos.get_user_id_by_operator_reply(
        operator_chat_id=settings.operator_id,
        forwarded_message_id=replied_id,
    )
    if user_id is None:
        await message.answer(
            "Не смог сопоставить reply с пользователем. "
            "Ответьте на последнее сообщение бота по этому тикету."
        )
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Пока поддерживаю только текстовые ответы оператором.")
        return

    await message.bot.send_message(user_id, text, parse_mode=None)
    await repos.log_message(
        user_id=user_id,
        direction="operator_in",
        msg_type="text",
        text=text,
    )
