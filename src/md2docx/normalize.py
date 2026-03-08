from __future__ import annotations

import re
import unicodedata

_SPACE_RE = re.compile(r"\s+")
_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*[\.、]?\s*|"
    r"[（(]?[一二三四五六七八九十百千万]+[）)]?[、\.]?\s*|"
    r"[ivxlcdmIVXLCDM]+[\.、)]\s*"
    r")+"
)


def normalize_heading(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.strip()
    value = _PREFIX_RE.sub("", value)
    value = _SPACE_RE.sub(" ", value)
    return value.lower()

