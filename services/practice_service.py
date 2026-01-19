from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from utils.text_norm import normalize_text


class PracticeServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PracticePhrase:
    phrase_id: str
    file_path: str
    expected_text: str
    keywords: list[str]


@dataclass(frozen=True, slots=True)
class PracticeScore:
    score: float
    found_keywords: list[str]
    missing_keywords: list[str]


@dataclass(slots=True)
class PracticeService:
    practice_sets_path: str

    def load_phrases(self) -> list[PracticePhrase]:
        path = Path(self.practice_sets_path)
        if not path.exists():
            raise PracticeServiceError(
                f"Practice sets file not found: {self.practice_sets_path}"
            )

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise PracticeServiceError("Practice sets JSON must be a list")

        phrases: list[PracticePhrase] = []
        for item in raw:
            phrases.append(
                PracticePhrase(
                    phrase_id=str(item.get("id", "")),
                    file_path=str(item.get("file", "")),
                    expected_text=str(item.get("expected_text", "")),
                    keywords=list(item.get("keywords", [])),
                )
            )
        return phrases

    def score_keywords(self, *, transcript: str, keywords: list[str]) -> PracticeScore:
        normalized = normalize_text(transcript)
        token_set = set(normalized.tokens)

        cleaned_keywords = [k.strip().lower() for k in keywords if str(k).strip()]
        unique_keywords: list[str] = []
        seen: set[str] = set()
        for k in cleaned_keywords:
            if k in seen:
                continue
            unique_keywords.append(k)
            seen.add(k)

        if not unique_keywords:
            return PracticeScore(score=0.0, found_keywords=[], missing_keywords=[])

        found = [k for k in unique_keywords if k in token_set]
        missing = [k for k in unique_keywords if k not in token_set]
        score = len(found) / len(unique_keywords)
        return PracticeScore(score=score, found_keywords=found, missing_keywords=missing)

