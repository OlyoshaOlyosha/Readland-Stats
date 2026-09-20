"""Runtime settings persisted to data/settings.json.

Cached in memory. save() invalidates the cache.
Missing / broken file → falls back to config defaults.
"""

import json
from pathlib import Path

from app import config

SETTINGS_PATH: Path = config.BASE_DIR / "data" / "settings.json"

DEFAULTS: dict = {
    "mature_days": config.MATURE_DAYS,
    "young_days": config.YOUNG_DAYS,
}

_cache: dict | None = None


def _read() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)
    return {**DEFAULTS, **{k: data[k] for k in DEFAULTS if k in data}}


def load() -> dict:
    """Current settings. First call reads file, later calls hit memory."""
    global _cache
    if _cache is None:
        _cache = _read()
    return _cache


def save(patch: dict) -> dict:
    """Patch current settings, persist, invalidate cache. Ignores unknown keys."""
    global _cache
    current = dict(load())
    for k in DEFAULTS:
        if k in patch and patch[k] is not None:
            current[k] = max(1, int(patch[k]))
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    _cache = current
    return current
