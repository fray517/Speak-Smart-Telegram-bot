import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove
from aiogram.types.input_file import FSInputFile

from handlers.states import Mode
from services.audio_service import AudioService
from services.audio_service import AudioServiceError
from services.practice_service import PracticePhrase
from services.practice_service import PracticeService
from services.practice_service import PracticeServiceError
from services.speech.base import SpeechRecognizer
from services.speech.base import SpeechRecognizerError
from storage.repositories import Repositories
from utils.config import Settings


logger = logging.getLogger(__name__)

router = Router()

BTN_NEXT = "Следующая"
BTN_REPEAT = "Повтор"
BTN_EXIT = "Выход"


def _practice_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEXT), KeyboardButton(text=BTN_REPEAT)],
            [KeyboardButton(text=BTN_EXIT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Следующая / Повтор / Выход",
    )


async def _send_practice_prompt(
    message: Message,
    *,
    repos: Repositories,
    phrase: PracticePhrase,
) -> None:
    voice_path = Path(phrase.file_path)
    if voice_path.exists():
        await message.answer_voice(FSInputFile(str(voice_path)))
        await repos.log_message(
            user_id=message.from_user.id,  # type: ignore[union-attr]
            direction="out",
            msg_type="voice",
            file_id=str(voice_path),
            text=f"practice_prompt:{phrase.phrase_id}",
        )
        return

    text = (
        "Я готов начать, но у меня пока нет аудио-файла для этой фразы.\n\n"
        f"Ожидаемый файл: {phrase.file_path}\n"
        "Положите voice prompts в папку assets и повторите /practice."
    )
    await message.answer(text)
    await repos.log_message(
        user_id=message.from_user.id,  # type: ignore[union-attr]
        direction="error",
        msg_type="text",
        text=f"Missing prompt audio: {phrase.file_path}",
    )


@router.message(Command("practice"))
async def cmd_practice(
    message: Message,
    state: FSMContext,
    repos: Repositories,
    settings: Settings,
) -> None:
    await state.set_state(Mode.practice_wait_answer)

    service = PracticeService(practice_sets_path=settings.practice_sets_path)
    try:
        phrases = service.load_phrases()
    except PracticeServiceError:
        logger.exception("Failed to load practice sets")
        await message.answer("Не удалось загрузить набор фраз для практики.")
        return

    if not phrases:
        await message.answer("Набор фраз пуст. Проверьте assets/practice_sets.json.")
        return

    await state.update_data(practice_idx=0)

    await message.answer(
        "Режим Practice включён.\n\n"
        "Я пришлю фразу голосом. Ответьте voice-сообщением.\n"
        "Распознанный текст я не показываю — только итоговый фидбек.",
        reply_markup=_practice_keyboard(),
    )
    await _send_practice_prompt(message, repos=repos, phrase=phrases[0])


@router.message(Mode.practice_wait_answer)
async def on_practice_message(
    message: Message,
    repos: Repositories,
    audio_service: AudioService,
    speech_recognizer: SpeechRecognizer,
    settings: Settings,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    user_id = message.from_user.id

    service = PracticeService(practice_sets_path=settings.practice_sets_path)
    try:
        phrases = service.load_phrases()
    except PracticeServiceError:
        logger.exception("Failed to load practice sets")
        await message.answer("Не удалось загрузить набор фраз для практики.")
        return

    if not phrases:
        await message.answer("Набор фраз пуст. Проверьте assets/practice_sets.json.")
        return

    if message.text:
        action = message.text.strip()
        data = await state.get_data()
        idx = int(data.get("practice_idx", 0))

        if action == BTN_EXIT:
            await state.clear()
            await message.answer(
                "Ок, выходим из Practice.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if action == BTN_REPEAT:
            await _send_practice_prompt(message, repos=repos, phrase=phrases[idx])
            return

        if action == BTN_NEXT:
            idx = (idx + 1) % len(phrases)
            await state.update_data(practice_idx=idx)
            await _send_practice_prompt(message, repos=repos, phrase=phrases[idx])
            return

    if message.voice is None:
        await message.answer(
            "Пришлите голосовое сообщение (voice) или используйте кнопки "
            "Следующая/Повтор/Выход."
        )
        return

    data = await state.get_data()
    idx = int(data.get("practice_idx", 0))
    phrase = phrases[idx]

    source_path = ""
    wav_path = ""
    try:
        source_path = await audio_service.download_voice(
            bot=message.bot,
            file_id=message.voice.file_id,
        )
        wav_path = audio_service.convert_to_wav(source_path=source_path)
        result = await speech_recognizer.transcribe(wav_path=wav_path)

        await repos.log_message(
            user_id=user_id,
            direction="in_transcript",
            msg_type="text",
            text=f"practice:{phrase.phrase_id}:{result.text}",
        )

        score = service.score_keywords(transcript=result.text, keywords=phrase.keywords)
        hint = ""
        if score.missing_keywords:
            hint = " Подсказка (ключевые слова): " + ", ".join(score.missing_keywords[:6])

        if score.score >= 0.8:
            feedback = "Правильно! Отлично."
        elif score.score >= 0.5:
            feedback = "Почти! Попробуйте ещё раз."
        else:
            feedback = "Давайте повторим. Попробуйте сказать фразу точнее."

        await message.answer(feedback + hint, reply_markup=_practice_keyboard())
    except (AudioServiceError, SpeechRecognizerError) as exc:
        logger.exception("Practice pipeline error")
        await message.answer(
            "Не удалось обработать голосовое сообщение. "
            "Проверьте настройку ffmpeg и распознавания."
        )
        await repos.log_message(
            user_id=user_id,
            direction="error",
            msg_type="text",
            text=str(exc),
        )
    finally:
        for path in (source_path, wav_path):
            if not path:
                continue
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to delete temp file: %s", path)

