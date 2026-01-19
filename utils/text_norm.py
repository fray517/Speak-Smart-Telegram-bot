from __future__ import annotations

import re
from dataclasses import dataclass


_TOKEN_RE = re.compile(r"[a-z0-9']+", flags=re.IGNORECASE)


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
    text = (text or "").lower().strip()
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    return NormalizedText(text=text, tokens=tokens)

