from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PromptGenerationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PracticeItem:
    item_id: str
    file_path: str
    expected_text: str


def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _load_dotenv(path: Path) -> None:
    """
    Minimal .env loader.

    Supports lines like KEY=VALUE and ignores blank lines and comments (#...).
    Values are loaded only if the key is not already in the environment.
    """
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise PromptGenerationError(f"File not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise PromptGenerationError("practice_sets.json must be a JSON list")
    return raw


def _parse_items(raw: list[dict[str, Any]]) -> list[PracticeItem]:
    items: list[PracticeItem] = []
    for obj in raw:
        item_id = str(obj.get("id", "")).strip()
        file_path = str(obj.get("file", "")).strip()
        expected_text = str(obj.get("expected_text", "")).strip()

        if not item_id:
            raise PromptGenerationError("Item has empty 'id'")
        if not file_path:
            raise PromptGenerationError(f"Item {item_id} has empty 'file'")
        if not expected_text:
            raise PromptGenerationError(
                f"Item {item_id} has empty 'expected_text'"
            )

        items.append(
            PracticeItem(
                item_id=item_id,
                file_path=file_path,
                expected_text=expected_text,
            )
        )
    return items


def _resolve_ffmpeg_path(cli_ffmpeg: str | None) -> str:
    if cli_ffmpeg:
        return cli_ffmpeg

    env_ffmpeg = os.environ.get("FFMPEG_PATH", "").strip()
    if env_ffmpeg:
        return env_ffmpeg

    raise PromptGenerationError(
        "FFMPEG_PATH is not set. Provide --ffmpeg or set FFMPEG_PATH in env/.env"
    )


def _convert_to_ogg(
    *,
    ffmpeg_path: str,
    source_audio_path: Path,
    target_ogg_path: Path,
) -> None:
    ffmpeg = Path(ffmpeg_path)
    if not ffmpeg.exists():
        raise PromptGenerationError(f"ffmpeg.exe not found: {ffmpeg_path}")

    target_ogg_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(ffmpeg),
        "-y",
        "-i",
        str(source_audio_path),
        "-c:a",
        "libopus",
        "-b:a",
        "32k",
        str(target_ogg_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PromptGenerationError(
            "ffmpeg failed to convert synthesized audio to .ogg. "
            f"stderr: {result.stderr.strip()}"
        )


async def _synthesize_edge_mp3(
    *,
    text: str,
    voice: str,
    target_mp3_path: Path,
) -> None:
    try:
        import edge_tts  # type: ignore
    except Exception as exc:
        raise PromptGenerationError(
            "Package 'edge-tts' is not installed. Install it with:\n"
            "python -m pip install edge-tts"
        ) from exc

    target_mp3_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text=text, voice=voice)
    try:
        await communicate.save(str(target_mp3_path))
    except Exception as exc:
        raise PromptGenerationError(
            "edge-tts failed to synthesize audio (often blocked by network/region). "
            "Try offline engine:\n"
            "python .\\scripts\\generate_practice_prompts.py --engine pyttsx3"
        ) from exc


async def _synthesize_gtts_mp3(*, text: str, target_mp3_path: Path) -> None:
    try:
        from gtts import gTTS  # type: ignore
    except Exception as exc:
        raise PromptGenerationError(
            "Package 'gTTS' is not installed. Install it with:\n"
            "python -m pip install gTTS"
        ) from exc

    def _save() -> None:
        target_mp3_path.parent.mkdir(parents=True, exist_ok=True)
        gTTS(text=text, lang="en").save(str(target_mp3_path))

    await _run_sync(_save)


async def _synthesize_pyttsx3_wav(*, text: str, target_wav_path: Path) -> None:
    try:
        import pyttsx3  # type: ignore
    except Exception as exc:
        raise PromptGenerationError(
            "Package 'pyttsx3' is not installed. Install it with:\n"
            "python -m pip install pyttsx3"
        ) from exc

    def _save() -> None:
        target_wav_path.parent.mkdir(parents=True, exist_ok=True)
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.save_to_file(text, str(target_wav_path))
        engine.runAndWait()

    await _run_sync(_save)


async def _synthesize_temp_audio(
    *,
    engine: str,
    text: str,
    voice: str,
    tmp_dir: Path,
) -> Path:
    engine = engine.strip().lower()

    if engine == "edge":
        path = tmp_dir / f"{uuid.uuid4().hex}.mp3"
        try:
            await _synthesize_edge_mp3(text=text, voice=voice, target_mp3_path=path)
        except PromptGenerationError:
            # Edge may be blocked by network/region (403). On Windows it's common,
            # so we fall back to offline engine.
            path.unlink(missing_ok=True)
            engine = "pyttsx3"
        else:
            return path

    if engine == "pyttsx3":
        path = tmp_dir / f"{uuid.uuid4().hex}.wav"
        await _synthesize_pyttsx3_wav(text=text, target_wav_path=path)
        return path

    if engine == "gtts":
        path = tmp_dir / f"{uuid.uuid4().hex}.mp3"
        await _synthesize_gtts_mp3(text=text, target_mp3_path=path)
        return path

    raise PromptGenerationError(f"Unsupported engine: {engine}")


async def run(args: argparse.Namespace) -> int:
    _load_dotenv(Path(args.dotenv))

    json_path = Path(args.practice_sets)
    raw = _load_json(json_path)
    items = _parse_items(raw)

    ffmpeg_path = _resolve_ffmpeg_path(args.ffmpeg)

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for idx, item in enumerate(items, start=1):
        out_path = Path(item.file_path)
        if out_path.exists() and not args.overwrite:
            print(f"[{idx}/{len(items)}] SKIP exists: {out_path}")
            continue

        tmp_audio: Path | None = None
        try:
            print(f"[{idx}/{len(items)}] TTS {item.item_id} -> {out_path}")
            tmp_audio = await _synthesize_temp_audio(
                engine=args.engine,
                text=item.expected_text,
                voice=args.voice,
                tmp_dir=tmp_dir,
            )
            _convert_to_ogg(
                ffmpeg_path=ffmpeg_path,
                source_audio_path=tmp_audio,
                target_ogg_path=out_path,
            )
        finally:
            try:
                if tmp_audio is not None:
                    tmp_audio.unlink(missing_ok=True)
            except OSError:
                pass

    print("Done.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate voice prompts (.ogg) for Practice set from assets/practice_sets.json"
        )
    )
    parser.add_argument(
        "--dotenv",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--practice-sets",
        dest="practice_sets",
        default="assets/practice_sets.json",
        help="Path to practice_sets.json",
    )
    parser.add_argument(
        "--voice",
        default="en-US-JennyNeural",
        help="Edge TTS voice name (e.g., en-US-JennyNeural)",
    )
    parser.add_argument(
        "--engine",
        default=("pyttsx3" if sys.platform == "win32" else "edge"),
        help=(
            "TTS engine: edge | pyttsx3 | gtts "
            "(default: pyttsx3 on Windows, edge on others)"
        ),
    )
    parser.add_argument(
        "--ffmpeg",
        default=None,
        help="Explicit path to ffmpeg.exe (overrides FFMPEG_PATH)",
    )
    parser.add_argument(
        "--tmp-dir",
        default="data/tmp_tts",
        help="Temporary directory for synthesized audio",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .ogg files",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())

