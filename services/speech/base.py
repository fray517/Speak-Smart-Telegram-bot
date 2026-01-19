from __future__ import annotations

from dataclasses import dataclass


class SpeechRecognizerError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SpeechResult:
    text: str


class SpeechRecognizer:
    async def transcribe(self, *, wav_path: str) -> SpeechResult:
        raise NotImplementedError

