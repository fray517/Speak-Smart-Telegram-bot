import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove

from handlers.states import Mode
from services.faq_service import FaqService
from services.faq_service import FaqServiceError
from storage.repositories import Repositories
from utils.config import Settings


logger = logging.getLogger(__name__)

router = Router()

BTN_ESCALATE = "Передать оператору"
BTN_BACK = "Назад"

FAQ_MIN_SCORE = 0.34


def _support_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_ESCALATE)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Введите вопрос или выберите действие",
    )


def _operator_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Закрыть тикет",
                    callback_data=f"close_ticket:{ticket_id}",
                )
            ]
        ]
    )


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    await state.set_state(Mode.support_wait_question)
    await message.answer(
        "Режим Support включён.\n\n"
        "Напишите ваш вопрос — я попробую найти ответ в FAQ.\n"
        "Если не получится, предложу передать оператору.",
        reply_markup=_support_keyboard(),
    )


@router.message(Mode.support_wait_question)
async def on_support_question(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    settings: Settings,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if message.text:
        text = message.text.strip()
        if text == BTN_BACK:
            await state.clear()
            await message.answer(
                "Ок, выходим из Support.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        faq = FaqService(faq_path=settings.faq_path)
        try:
            match = faq.find_best_answer(query=text)
        except FaqServiceError:
            logger.exception("FAQ load/search error")
            await message.answer(
                "Сейчас не могу открыть базу FAQ. "
                "Можете передать вопрос оператору.",
                reply_markup=_support_keyboard(),
            )
            return

        if match is not None and match.score >= FAQ_MIN_SCORE and match.item.answer:
            await message.answer(match.item.answer, reply_markup=_support_keyboard())
            await repos.log_message(
                user_id=message.from_user.id,
                direction="out",
                msg_type="text",
                text=f"faq_answer(score={match.score:.2f})",
            )
            return

        await state.set_state(Mode.support_wait_escalation)
        await state.update_data(last_question=text)
        await message.answer(
            "Похоже, в FAQ нет точного ответа.\n\n"
            "Передать вопрос оператору?",
            reply_markup=_support_keyboard(),
        )
        return

    await message.answer("Пришлите вопрос текстом.")


@router.message(Mode.support_wait_escalation)
async def on_support_escalation(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    settings: Settings,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if not message.text:
        await message.answer(
            "Пожалуйста, используйте кнопки: Передать оператору / Назад.",
            reply_markup=_support_keyboard(),
        )
        return

    action = message.text.strip()
    if action == BTN_BACK:
        await state.set_state(Mode.support_wait_question)
        await message.answer(
            "Ок. Напишите вопрос ещё раз — попробую поискать в FAQ.",
            reply_markup=_support_keyboard(),
        )
        return

    if action != BTN_ESCALATE:
        await message.answer(
            "Пожалуйста, используйте кнопки: Передать оператору / Назад.",
            reply_markup=_support_keyboard(),
        )
        return

    data = await state.get_data()
    question = str(data.get("last_question", "")).strip()
    if not question:
        await state.set_state(Mode.support_wait_question)
        await message.answer(
            "Не вижу текста вопроса. Напишите вопрос ещё раз.",
            reply_markup=_support_keyboard(),
        )
        return

    user_id = message.from_user.id
    ticket_id = await repos.get_open_ticket_by_user(user_id=user_id)
    if ticket_id is None:
        ticket_id = await repos.create_ticket(user_id=user_id, last_user_message=question)
    else:
        await repos.update_ticket_last_message(
            ticket_id=ticket_id,
            last_user_message=question,
        )

    username = message.from_user.username or "-"
    operator_text = (
        f"Новый тикет #{ticket_id}\n"
        f"user_id: {user_id}\n"
        f"username: @{username}\n\n"
        f"Вопрос:\n{question}"
    )
    try:
        sent = await message.bot.send_message(
            settings.operator_id,
            operator_text,
            parse_mode=None,
            reply_markup=_operator_ticket_keyboard(ticket_id),
        )
        await repos.save_operator_map(
            operator_chat_id=settings.operator_id,
            forwarded_message_id=sent.message_id,
            user_id=user_id,
        )
        logger.info(
            "Operator notified: ticket=%s operator_id=%s message_id=%s user_id=%s",
            ticket_id,
            settings.operator_id,
            sent.message_id,
            user_id,
        )
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        logger.exception("Failed to notify operator (ticket=%s)", ticket_id)
        await repos.log_message(
            user_id=user_id,
            direction="error",
            msg_type="text",
            text=f"operator_notify_failed:{ticket_id}:{exc}",
        )
        await message.answer(
            "Я не смог отправить сообщение оператору.\n\n"
            "Чаще всего это происходит, если оператор ещё не открывал чат с ботом.\n"
            "Попросите оператора написать боту /start, затем повторите эскалацию.\n\n"
            "Если оператор уже писал боту, проверьте, что OPERATOR_ID указан верно.",
            reply_markup=_support_keyboard(),
        )
        await state.set_state(Mode.support_wait_question)
        return

    await repos.log_message(
        user_id=user_id,
        direction="operator_out",
        msg_type="text",
        text=f"ticket_notify:{ticket_id}",
    )

    await state.set_state(Mode.operator_active)
    await state.update_data(ticket_id=ticket_id)
    await message.answer(
        f"Готово. Я передал вопрос оператору. Номер тикета: #{ticket_id}.\n"
        "Ожидайте ответа.",
        reply_markup=_support_keyboard(),
    )


@router.message(Mode.operator_active)
async def on_operator_active(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    settings: Settings,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if message.text and message.text.strip() == BTN_BACK:
        await state.clear()
        await message.answer(
            "Ок. Вы вышли из режима ожидания оператора.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    if isinstance(ticket_id, int) and message.text:
        await repos.update_ticket_last_message(
            ticket_id=ticket_id,
            last_user_message=message.text.strip(),
        )
        try:
            sent = await message.bot.send_message(
                settings.operator_id,
                "Тикет #{ticket_id}: пользователь дополнил сообщение:\n"
                f"{message.text.strip()}",
                parse_mode=None,
                reply_markup=_operator_ticket_keyboard(ticket_id),
            )
            await repos.save_operator_map(
                operator_chat_id=settings.operator_id,
                forwarded_message_id=sent.message_id,
                user_id=message.from_user.id,
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            logger.exception("Failed to notify operator (ticket=%s)", ticket_id)

    await message.answer(
        "Я передал ваш вопрос оператору. Пожалуйста, ожидайте ответа.\n"
        "Если хотите выйти — нажмите «Назад».",
        reply_markup=_support_keyboard(),
    )

