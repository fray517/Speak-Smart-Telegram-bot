from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from utils.text_norm import normalize_text


class FaqServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FaqItem:
    question: str
    keywords: list[str]
    answer: str


@dataclass(frozen=True, slots=True)
class FaqMatch:
    item: FaqItem
    score: float


@dataclass(slots=True)
class FaqService:
    faq_path: str

    def load(self) -> list[FaqItem]:
        path = Path(self.faq_path)
        if not path.exists():
            raise FaqServiceError(f"FAQ file not found: {self.faq_path}")

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise FaqServiceError("FAQ JSON must be a list")

        items: list[FaqItem] = []
        for obj in raw:
            question = str(obj.get("q", ""))
            base_keywords = [
                str(k).strip().casefold() for k in obj.get("keywords", [])
            ]
            question_tokens = normalize_text(question).tokens
            merged_keywords = list(dict.fromkeys(base_keywords + question_tokens))

            items.append(
                FaqItem(
                    question=question,
                    keywords=merged_keywords,
                    answer=str(obj.get("a", "")),
                )
            )
        return items

    def find_best_answer(self, *, query: str) -> FaqMatch | None:
        normalized = normalize_text(query)
        token_set = set(normalized.tokens)
        if not token_set:
            return None

        best: FaqMatch | None = None
        for item in self.load():
            keywords = [k for k in item.keywords if k]
            if not keywords:
                continue

            unique_keywords = list(dict.fromkeys(keywords))
            found = sum(1 for k in unique_keywords if k in token_set)
            if found == 0:
                continue

            score = found / len(unique_keywords)
            if best is None or score > best.score:
                best = FaqMatch(item=item, score=score)

        return best

