from __future__ import annotations

import re
from dataclasses import dataclass


# Latin + Cyrillic (incl. ё) + digits + apostrophe, for simple keyword matching.
_TOKEN_RE = re.compile(r"[0-9a-zа-яё']+", flags=re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NormalizedText:
    text: str
    tokens: list[str]


def normalize_text(text: str) -> NormalizedText:
    """
    Normalize text for simple keyword matching.

    - lowercase
    - extract tokens (latin letters, digits, apostrophe)
    """
    text = (text or "").casefold().strip()
    tokens = [t.casefold() for t in _TOKEN_RE.findall(text)]
    return NormalizedText(text=text, tokens=tokens)

