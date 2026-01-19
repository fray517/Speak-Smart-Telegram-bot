from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot


@dataclass(frozen=True, slots=True)
class AudioFiles:
    source_path: str
    wav_path: str


class AudioServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class AudioService:
    ffmpeg_path: str
    workdir: str = "data/tmp"

    async def download_voice(self, *, bot: Bot, file_id: str) -> str:
        workdir = Path(self.workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        tg_file = await bot.get_file(file_id)
        ext = Path(tg_file.file_path or "").suffix or ".ogg"
        target = workdir / f"{uuid.uuid4().hex}{ext}"
        await bot.download_file(tg_file.file_path, destination=target)
        return str(target)

    def convert_to_wav(self, *, source_path: str) -> str:
        source = Path(source_path)
        if not source.exists():
            raise AudioServiceError(f"Audio source does not exist: {source_path}")

        ffmpeg = Path(self.ffmpeg_path)
        if not ffmpeg.exists():
            raise AudioServiceError(
                f"ffmpeg.exe not found at FFMPEG_PATH: {self.ffmpeg_path}"
            )

        workdir = Path(self.workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        target = workdir / f"{uuid.uuid4().hex}.wav"
        cmd = [
            str(ffmpeg),
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(target),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise AudioServiceError(
                "ffmpeg failed to convert audio to wav. "
                f"stderr: {result.stderr.strip()}"
            )

        return str(target)

