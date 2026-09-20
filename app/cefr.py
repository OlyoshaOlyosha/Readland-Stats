"""CEFR level lookup. Loads the dataset once, caches in memory.

Expected CSV columns (flexible matching): Word + CEFR.
Missing file → empty dict, all lookups return None.
"""

import csv
from functools import lru_cache

from app import config

LEVEL_NUM = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

_WORD_KEYS = ("word", "headword", "term", "lemma")
_LEVEL_KEYS = ("cefr", "cefr_level", "level")


def _find_col(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {f.lower(): f for f in fieldnames or []}
    for c in candidates:
        if c in lower:
            return lower[c]
    return None


@lru_cache(maxsize=1)
def load_levels() -> dict[str, str]:
    """Return {word_lower: level}. Cached for the process lifetime."""
    path = config.CEFR_PATH
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        word_col = _find_col(reader.fieldnames or [], _WORD_KEYS)
        level_col = _find_col(reader.fieldnames or [], _LEVEL_KEYS)
        if not word_col or not level_col:
            return {}
        for row in reader:
            w = (row.get(word_col) or "").strip().lower()
            lvl = (row.get(level_col) or "").strip().upper()
            if w and lvl in LEVEL_NUM:
                out[w] = lvl
    return out


def _stem_candidates(word: str) -> list[str]:
    """Possible base forms for regular English inflections. Order = priority."""
    w = word.lower()
    out: list[str] = []
    if len(w) > 4 and w.endswith("ies"):
        out.append(w[:-3] + "y")
    if len(w) > 3 and w.endswith("es"):
        out.append(w[:-2])
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        out.append(w[:-1])
    if len(w) > 5 and w.endswith("ing"):
        out.append(w[:-3])
        out.append(w[:-3] + "e")
    if len(w) > 4 and w.endswith("ed"):
        out.append(w[:-2])
        out.append(w[:-1])
    return out


def _lookup_one(word: str) -> str | None:
    """Single-word lookup with stem fallback. None if no match."""
    levels = load_levels()
    w = word.strip().lower()
    if not w:
        return None
    if w in levels:
        return levels[w]
    for stem in _stem_candidates(w):
        if stem in levels:
            return levels[stem]
    return None


def get_level(text: str) -> str | None:
    """CEFR level for a word or a phrase.

    Single word: direct lookup, then stem fallback.
    Phrase: split by whitespace, look up each word, return the highest level.
    """
    text = (text or "").strip()
    if not text:
        return None
    tokens = text.split()
    if len(tokens) == 1:
        return _lookup_one(tokens[0])
    found = [lvl for lvl in (_lookup_one(t) for t in tokens) if lvl]
    if not found:
        return None
    return max(found, key=lambda l: LEVEL_NUM[l])


def get_level_num(word: str) -> int | None:
    """Numeric CEFR level (A1=1 … C2=6), or None."""
    lvl = get_level(word)
    return LEVEL_NUM.get(lvl) if lvl else None
