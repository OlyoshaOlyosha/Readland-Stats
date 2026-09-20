"""HTTP endpoints for words CRUD and stats."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import cefr, config, data_manager, settings, stats

router = APIRouter()


class WordPatch(BaseModel):
    word: str | None = None
    translation: str | None = None
    contexts: str | None = None


class SettingsPatch(BaseModel):
    mature_days: int | None = None
    young_days: int | None = None


class BulkWordPatch(BaseModel):
    word: str  # anchor: existing value in the dictionary
    new_word: str | None = None  # optional rename target
    translation: str | None = None
    contexts: str | None = None


@router.get("/api/words")
def list_words() -> list[dict]:
    """All words, enriched with CEFR level and is_phrase flag for the editor."""
    return [
        {**w.__dict__, "level": cefr.get_level(w.word), "is_phrase": " " in w.word.strip()}
        for w in data_manager.load_words()
    ]


@router.patch("/api/words/{idx}")
def patch_word(idx: int, patch: WordPatch) -> dict:
    words = data_manager.load_words()
    if not 0 <= idx < len(words):
        raise HTTPException(404, "Word index out of range")
    w = words[idx]

    if patch.word is not None and patch.word != w.word:
        new_word = patch.word.strip()
        if not new_word:
            raise HTTPException(400, "Word cannot be empty")
        contexts = patch.contexts if patch.contexts is not None else w.contexts
        if new_word.lower() not in contexts.lower():
            raise HTTPException(
                400,
                f"New word '{new_word}' not found in contexts. Update contexts too.",
            )
        for i, other in enumerate(words):
            if i != idx and other.word == new_word and other.language == w.language:
                raise HTTPException(
                    409,
                    f"Duplicate: '{new_word}' already exists for language '{w.language}'",
                )
        w.word = new_word

    if patch.translation is not None:
        w.translation = patch.translation
    if patch.contexts is not None:
        w.contexts = patch.contexts

    data_manager.save_words(words)
    return {"ok": True, "word": w.__dict__}


@router.get("/api/stats/overview")
def stats_overview() -> dict:
    return stats.overview()


@router.get("/api/stats/srs")
def stats_srs(days: int = 60) -> dict:
    return stats.srs_calendar(days)


@router.get("/api/stats/difficult")
def stats_difficult(limit: int = 30) -> list[dict]:
    return stats.difficult_words(limit)


@router.get("/api/stats/velocity")
def stats_velocity() -> dict:
    return stats.velocity()


def _human_size(n: int) -> str:
    """Format bytes as B/KB/MB/GB with one decimal."""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@router.get("/api/file-info")
def file_info() -> dict:
    """Info about the CSV file: existence, size, mtime, word count."""
    path = config.CSV_PATH
    if not path.exists():
        return {"exists": False, "path": str(path)}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "size_bytes": stat.st_size,
        "size_human": _human_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "words": len(data_manager.load_words()),
    }


@router.get("/api/stats/easiness-histogram")
def stats_easiness_histogram() -> dict:
    return stats.easiness_histogram()


@router.get("/api/stats/scatter")
def stats_scatter() -> list[dict]:
    return stats.scatter_data()


@router.get("/api/stats/due-soon")
def stats_due_soon(days: int = 1) -> list[dict]:
    return stats.due_soon(days)


@router.get("/api/stats/streak")
def stats_streak() -> dict:
    return stats.streak()


@router.get("/api/stats/heatmap")
def stats_heatmap(days: int = 365) -> dict:
    return stats.heatmap(days)


@router.get("/api/stats/weekly")
def stats_weekly(weeks: int = 12) -> dict:
    return stats.weekly_added(weeks)


@router.get("/api/stats/overdue")
def stats_overdue() -> list[dict]:
    return stats.overdue()


@router.get("/api/stats/avg-load")
def stats_avg_load(days: int = 30) -> dict:
    return stats.avg_load(days)


@router.get("/api/stats/cefr-profile")
def stats_cefr_profile() -> dict:
    return stats.cefr_profile()


@router.get("/api/stats/cefr-avg")
def stats_cefr_avg() -> dict:
    return stats.cefr_avg()


@router.get("/api/stats/cefr-by-easiness")
def stats_cefr_by_easiness() -> list[dict]:
    return stats.cefr_by_easiness()


@router.get("/api/settings")
def get_settings() -> dict:
    return settings.load()


@router.patch("/api/settings")
def patch_settings(patch: SettingsPatch) -> dict:
    return settings.save(patch.model_dump(exclude_none=True))


@router.post("/api/cefr/reload")
def cefr_reload() -> dict:
    """Drop the in-memory CEFR cache and re-read the dataset file."""
    cefr.load_levels.cache_clear()
    return {"ok": True, "words": len(cefr.load_levels())}


@router.get("/api/stats/avg-cost")
def stats_avg_cost() -> dict:
    return stats.avg_cost()


@router.get("/api/stats/next-year-heatmap")
def stats_next_year_heatmap(days: int = 365) -> dict:
    return stats.next_year_heatmap(days)


@router.get("/api/stats/interval-distribution")
def stats_interval_distribution() -> dict:
    return stats.interval_distribution()


@router.get("/api/stats/recall-ease")
def stats_recall_ease() -> dict:
    return stats.recall_ease_histogram()


@router.get("/api/stats/time-of-day")
def stats_time_of_day() -> dict:
    return stats.time_of_day()


@router.post("/api/words/bulk")
def bulk_patch_words(patches: list[BulkWordPatch]) -> dict:
    """Apply many word patches in one pass. One backup, one disk write.

    Anchor is `word` (must match an existing entry). Optional `new_word` renames.
    Invalid items are skipped and reported; valid ones are applied.
    """
    words = data_manager.load_words()
    by_word = {w.word: w for w in words}
    results: list[dict] = []
    applied = 0
    seen_new: set[str] = set()

    for p in patches:
        w = by_word.get(p.word)
        if w is None:
            results.append({"word": p.word, "ok": False, "error": "not found"})
            continue

        if p.new_word is not None and p.new_word != w.word:
            new = p.new_word.strip()
            if not new:
                results.append({"word": p.word, "ok": False, "error": "empty new_word"})
                continue
            if new.lower() in seen_new:
                results.append({"word": p.word, "ok": False, "error": "duplicate in batch"})
                continue
            dup = any(o is not w and o.word.lower() == new.lower() and o.language == w.language for o in words)
            if dup:
                results.append({"word": p.word, "ok": False, "error": "duplicate"})
                continue
            ctx = p.contexts if p.contexts is not None else w.contexts
            if new.lower() not in ctx.lower():
                results.append({"word": p.word, "ok": False, "error": "new word not in contexts"})
                continue
            seen_new.add(new.lower())
            w.word = new

        if p.translation is not None:
            w.translation = p.translation
        if p.contexts is not None:
            w.contexts = p.contexts

        results.append({"word": p.word, "ok": True})
        applied += 1

    backup_path = None
    if applied:
        backup_path = data_manager.backup_csv()
        data_manager.save_words(words)
    return {"applied": applied, "total": len(patches), "backup": backup_path, "results": results}
