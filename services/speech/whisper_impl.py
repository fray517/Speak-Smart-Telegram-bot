from __future__ import annotations

import asyncio
from dataclasses import dataclass

from services.speech.base import SpeechRecognizer
from services.speech.base import SpeechRecognizerError
from services.speech.base import SpeechResult


@dataclass(slots=True)
class WhisperRecognizer(SpeechRecognizer):
    model_name: str
    _model: object | None = None
    _backend: str | None = None

    def _load_model(self) -> None:
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel  # type: ignore

            # IMPORTANT (Windows/MVP): Force CPU mode to avoid CUDA DLL issues
            # like "cublas64_12.dll is not found".
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
            )
            self._backend = "faster-whisper"
            return
        except Exception:
            pass

        try:
            import whisper  # type: ignore

            self._model = whisper.load_model(self.model_name)
            self._backend = "openai-whisper"
            return
        except Exception as exc:
            raise SpeechRecognizerError(
                "Whisper backend is not available. "
                "Install one of: faster-whisper or openai-whisper. "
                "Example: pip install faster-whisper"
            ) from exc

    async def transcribe(self, *, wav_path: str) -> SpeechResult:
        self._load_model()
        assert self._model is not None
        assert self._backend is not None

        loop = asyncio.get_running_loop()
        try:
            text = await loop.run_in_executor(None, self._transcribe_sync, wav_path)
        except Exception as exc:
            raise SpeechRecognizerError(
                "Whisper failed to transcribe audio. "
                "If you use faster-whisper on Windows, ensure CPU mode is used."
            ) from exc

        return SpeechResult(text=text.strip())

    def _transcribe_sync(self, wav_path: str) -> str:
        assert self._model is not None
        assert self._backend is not None

        if self._backend == "faster-whisper":
            segments, _info = self._model.transcribe(wav_path)  # type: ignore[attr-defined]
            return " ".join(segment.text for segment in segments)

        if self._backend == "openai-whisper":
            result = self._model.transcribe(wav_path)  # type: ignore[attr-defined]
            return str(result.get("text", ""))

        raise SpeechRecognizerError(f"Unknown whisper backend: {self._backend}")

