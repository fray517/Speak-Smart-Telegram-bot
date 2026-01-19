from __future__ import annotations

from services.speech.base import SpeechRecognizer
from services.speech.base import SpeechRecognizerError
from services.speech.whisper_impl import WhisperRecognizer


class DisabledRecognizer(SpeechRecognizer):
    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def transcribe(self, *, wav_path: str):  # type: ignore[override]
        raise SpeechRecognizerError(self._reason)


def build_speech_recognizer(*, provider: str, whisper_model: str) -> SpeechRecognizer:
    provider = provider.strip().lower()

    if provider == "whisper":
        try:
            return WhisperRecognizer(model_name=whisper_model)
        except SpeechRecognizerError as exc:
            return DisabledRecognizer(str(exc))

    return DisabledRecognizer(f"Unsupported speech provider: {provider}")

