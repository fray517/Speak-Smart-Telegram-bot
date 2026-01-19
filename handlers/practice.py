import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.states import Mode
from services.audio_service import AudioService
from services.audio_service import AudioServiceError
from services.speech.base import SpeechRecognizer
from services.speech.base import SpeechRecognizerError
from storage.repositories import Repositories


logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("practice"))
async def cmd_practice(message: Message, state: FSMContext) -> None:
    await state.set_state(Mode.practice_wait_answer)
    await message.answer(
        "Режим Practice включён.\n\n"
        "Пришлите голосовое сообщение в ответ. "
        "Пока что я проверяю только цепочку скачивания/конвертации/распознавания."
    )


@router.message(Mode.practice_wait_answer)
async def on_practice_message(
    message: Message,
    repos: Repositories,
    audio_service: AudioService,
    speech_recognizer: SpeechRecognizer,
) -> None:
    if message.voice is None:
        await message.answer("Пожалуйста, пришлите именно voice-сообщение.")
        return

    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    user_id = message.from_user.id

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
            text=result.text,
        )

        await message.answer(
            "Спасибо! Голосовое сообщение получено и обработано. "
            "Продолжаем."
        )
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

