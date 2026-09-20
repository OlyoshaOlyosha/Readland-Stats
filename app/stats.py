"""Compute analytics over the word list. Pure-Python; no pandas needed at this scale."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from app import settings
from app.cefr import LEVEL_ORDER, get_level, get_level_num
from app.data_manager import load_words


def _to_int(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _days_from_ms(ms) -> float:
    return _to_int(ms) / 86_400_000


def _status(w, mature_days: int, young_days: int) -> str:
    days = _days_from_ms(w.spaced_repetition_interval)
    if days >= mature_days:
        return "mature"
    if days >= young_days:
        return "young"
    if w.spaced_repetition_interval:
        return "learning"
    return "new"


def overview() -> dict:
    conf = settings.load()
    words = load_words()
    total = len(words)
    statuses = Counter(_status(w, conf["mature_days"], conf["young_days"]) for w in words)
    easily = [
        float(w.spaced_repetition_easiness_factor)
        for w in words
        if w.spaced_repetition_easiness_factor not in (None, "", "undefined")
    ]
    attempts = [
        _to_int(w.spaced_repetition_recall_attempts)
        for w in words
        if w.spaced_repetition_recall_attempts not in (None, "")
    ]
    return {
        "total": total,
        "by_status": dict(statuses),
        "avg_easiness": round(sum(easily) / len(easily), 3) if easily else 0,
        "total_attempts": sum(attempts),
        "mature_share": round(statuses.get("mature", 0) / total * 100, 1) if total else 0,
    }


def srs_calendar(days_ahead: int = 60) -> dict:
    """Count how many words are scheduled per day over the next N days."""
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, int] = defaultdict(int)
    for w in load_words():
        raw = w.spaced_repetition_next_date
        if not raw or raw == "undefined":
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        delta = (d - today).days
        if 0 <= delta <= days_ahead:
            buckets[d.isoformat()] += 1
    return {
        "days": sorted(buckets.keys()),
        "counts": [buckets[k] for k in sorted(buckets.keys())],
    }


def difficult_words(limit: int = 30) -> list[dict]:
    """Top-N most problematic words: high attempts, low easiness."""
    scored = []
    for w in load_words():
        attempts = _to_int(w.spaced_repetition_recall_attempts)
        ease = (
            float(w.spaced_repetition_easiness_factor)
            if w.spaced_repetition_easiness_factor not in (None, "", "undefined")
            else 2.5
        )
        if attempts == 0:
            continue
        scored.append({
            "word": w.word,
            "translation": w.translation,
            "attempts": attempts,
            "easiness": ease,
            "score": attempts / max(ease, 0.1),
        })
    scored.sort(key=lambda x: -x["score"])
    return scored[:limit]


def velocity() -> dict:
    """Cumulative word count over time, bucketed by day of `last_modified`."""
    by_day: Counter = Counter()
    for w in load_words():
        raw = w.last_modified
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
        by_day[d] += 1
    days = sorted(by_day)
    cumulative, running = [], 0
    for d in days:
        running += by_day[d]
        cumulative.append(running)
    return {"days": days, "added": [by_day[d] for d in days], "cumulative": cumulative}


EASINESS_BUCKETS = [
    ("< 1.5", 0.0, 1.5),
    ("1.5-1.8", 1.5, 1.8),
    ("1.8-2.1", 1.8, 2.1),
    ("2.1-2.4", 2.1, 2.4),
    ("2.4-2.7", 2.4, 2.7),
    (">= 2.7", 2.7, 99.0),
]


def easiness_histogram() -> dict:
    """Bucketed counts of easiness factor. One pass over the word list."""
    counts = [0] * len(EASINESS_BUCKETS)
    for w in load_words():
        raw = w.spaced_repetition_easiness_factor
        if raw in (None, "", "undefined"):
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        for i, (_, lo, hi) in enumerate(EASINESS_BUCKETS):
            if lo <= v < hi:
                counts[i] += 1
                break
    return {"labels": [b[0] for b in EASINESS_BUCKETS], "counts": counts}


def scatter_data() -> list[dict]:
    """Every word with at least one recall attempt.

    Includes multiple X-axis candidates (attempts, word_length, context_length)
    so the frontend can switch the axis without refetching.
    """
    conf = settings.load()
    out = []
    for w in load_words():
        attempts = _to_int(w.spaced_repetition_recall_attempts)
        if attempts == 0:
            continue
        ease = (
            float(w.spaced_repetition_easiness_factor)
            if w.spaced_repetition_easiness_factor not in (None, "", "undefined")
            else 2.5
        )
        first_ctx = (w.contexts or "").split("|")[0].strip()
        out.append({
            "word": w.word,
            "translation": w.translation,
            "contexts": w.contexts,
            "attempts": attempts,
            "easiness": ease,
            "level": get_level(w.word),
            "is_phrase": " " in w.word.strip(),
            "status": _status(w, conf["mature_days"], conf["young_days"]),
            "word_length": len(w.word.split()) if w.word else 0,
            "context_length": len(first_ctx),
        })
    return out


def due_soon(days: int = 1) -> list[dict]:
    """Words due within the next N days (0 = today). Sorted by due date."""
    today = datetime.now(timezone.utc).date()
    out = []
    for w in load_words():
        raw = w.spaced_repetition_next_date
        if not raw or raw == "undefined":
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        delta = (d - today).days
        if 0 <= delta <= days:
            out.append({
                "word": w.word,
                "translation": w.translation,
                "due": d.isoformat(),
                "days": delta,
                "level": get_level(w.word),
                "is_phrase": " " in w.word.strip(),
            })
    out.sort(key=lambda x: (x["days"], x["word"]))
    return out


def _activity_dates() -> set[str]:
    """Return set of ISO dates on which at least one word was added."""
    dates: set[str] = set()
    for w in load_words():
        raw = w.last_modified
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
        dates.add(d)
    return dates


def streak() -> dict:
    """Current and longest streak of consecutive days with at least one added word."""
    dates = sorted(_activity_dates())
    if not dates:
        return {"current": 0, "longest": 0, "last": None}

    longest = 1
    run = 1
    for i in range(1, len(dates)):
        prev = datetime.fromisoformat(dates[i - 1]).date()
        cur = datetime.fromisoformat(dates[i]).date()
        if (cur - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    # Current streak: walk back from today
    today = datetime.now(timezone.utc).date()
    current = 0
    cursor = today
    while cursor.isoformat() in dates:
        current += 1
        cursor -= timedelta(days=1)
    return {"current": current, "longest": longest, "last": dates[-1]}


def heatmap(days: int = 365) -> dict:
    """Daily counts of added words for the last N days (GitHub-style)."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)
    by_day: Counter = Counter()
    for w in load_words():
        raw = w.last_modified
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if start <= d <= today:
            by_day[d.isoformat()] += 1
    # Build continuous range (no gaps)
    out = []
    cursor = start
    while cursor <= today:
        iso = cursor.isoformat()
        out.append({"date": iso, "count": by_day.get(iso, 0)})
        cursor += timedelta(days=1)
    return {"days": out, "start": start.isoformat(), "end": today.isoformat()}


def weekly_added(weeks: int = 12) -> dict:
    """Words added per ISO week for the last N weeks."""
    today = datetime.now(timezone.utc).date()
    by_week: Counter = Counter()
    for w in load_words():
        raw = w.last_modified
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        iso_year, iso_week, _ = d.isocalendar()
        by_week[f"{iso_year}-W{iso_week:02d}"] += 1
    keys = sorted(by_week.keys())[-weeks:]
    return {"weeks": keys, "counts": [by_week[k] for k in keys]}


def overdue() -> list[dict]:
    """Words whose next_date is strictly in the past."""
    today = datetime.now(timezone.utc).date()
    out = []
    for w in load_words():
        raw = w.spaced_repetition_next_date
        if not raw or raw == "undefined":
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        delta = (d - today).days
        if delta < 0:
            out.append({
                "word": w.word,
                "translation": w.translation,
                "due": d.isoformat(),
                "overdue_days": abs(delta),
                "level": get_level(w.word),
                "is_phrase": " " in w.word.strip(),
            })
    out.sort(key=lambda x: -x["overdue_days"])
    return out


def avg_load(days: int = 30) -> dict:
    """Average and peak words due per day over the next N days."""
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, int] = defaultdict(int)
    for w in load_words():
        raw = w.spaced_repetition_next_date
        if not raw or raw == "undefined":
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        delta = (d - today).days
        if 0 <= delta <= days:
            buckets[d.isoformat()] += 1
    values = list(buckets.values())
    return {
        "avg": round(sum(values) / len(values), 1) if values else 0,
        "peak": max(values) if values else 0,
        "days": days,
    }


def cefr_profile() -> dict:
    """Count words per CEFR level. Words not in the dataset go to `unknown`."""
    counts = {lvl: 0 for lvl in LEVEL_ORDER}
    unknown = 0
    for w in load_words():
        lvl = get_level(w.word)
        if lvl:
            counts[lvl] += 1
        else:
            unknown += 1
    return {
        "labels": LEVEL_ORDER,
        "counts": [counts[lvl] for lvl in LEVEL_ORDER],
        "unknown": unknown,
    }


def cefr_avg() -> dict:
    """Average numeric CEFR level of the whole vocabulary (A1=1 … C2=6)."""
    nums = [n for n in (get_level_num(w.word) for w in load_words()) if n]
    return {
        "avg": round(sum(nums) / len(nums), 2) if nums else 0,
        "matched": len(nums),
    }


def cefr_by_easiness() -> list[dict]:
    """For each CEFR level: average easiness across words at that level."""
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for w in load_words():
        raw = w.spaced_repetition_easiness_factor
        if raw in (None, "", "undefined"):
            continue
        lvl = get_level(w.word)
        if not lvl:
            continue
        try:
            sums[lvl] += float(raw)
            counts[lvl] += 1
        except ValueError:
            continue
    return [
        {
            "level": lvl,
            "avg_easiness": round(sums[lvl] / counts[lvl], 3) if counts[lvl] else 0,
            "count": counts[lvl],
        }
        for lvl in LEVEL_ORDER
    ]


def avg_cost() -> dict:
    """Average recall attempts among words that reached 'mature' status."""
    conf = settings.load()
    costs = []
    for w in load_words():
        if _status(w, conf["mature_days"], conf["young_days"]) != "mature":
            continue
        attempts = _to_int(w.spaced_repetition_recall_attempts)
        if attempts > 0:
            costs.append(attempts)
    return {
        "avg": round(sum(costs) / len(costs), 2) if costs else 0,
        "count": len(costs),
    }


def next_year_heatmap(days: int = 365) -> dict:
    """Scheduled reviews per day for the next N days (GitHub-style grid)."""
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=days - 1)
    by_day: Counter = Counter()
    for w in load_words():
        raw = w.spaced_repetition_next_date
        if not raw or raw == "undefined":
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if today <= d <= end:
            by_day[d.isoformat()] += 1
    out = []
    cursor = today
    while cursor <= end:
        iso = cursor.isoformat()
        out.append({"date": iso, "count": by_day.get(iso, 0)})
        cursor += timedelta(days=1)
    return {"days": out, "start": today.isoformat(), "end": end.isoformat()}


# Interval buckets by days. Labels go straight to the chart.
INTERVAL_BUCKETS = [
    ("—", None),
    ("<1", (0.0, 1.0)),
    ("1-7", (1.0, 7.0)),
    ("7-30", (7.0, 30.0)),
    ("30-90", (30.0, 90.0)),
    ("90-180", (90.0, 180.0)),
    ("180-365", (180.0, 365.0)),
    ("365+", (365.0, float("inf"))),
]


def interval_distribution() -> dict:
    """Count words per interval bucket (days until next review grows)."""
    counts = [0] * len(INTERVAL_BUCKETS)
    for w in load_words():
        raw = w.spaced_repetition_interval
        if not raw or raw == "undefined":
            counts[0] += 1
            continue
        days = _days_from_ms(raw)
        placed = False
        for i, (_, bounds) in enumerate(INTERVAL_BUCKETS):
            if bounds is None:
                continue
            lo, hi = bounds
            if lo <= days < hi:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[0] += 1
    return {"labels": [b[0] for b in INTERVAL_BUCKETS], "counts": counts}


def recall_ease_histogram() -> dict:
    """Histogram of subjective recall ease (0 = forgot, 5 = easy)."""
    counts = [0] * 6
    for w in load_words():
        raw = w.spaced_repetition_last_recall_ease
        if raw in (None, "", "undefined"):
            continue
        try:
            v = int(float(raw))
        except ValueError:
            continue
        if 0 <= v <= 5:
            counts[v] += 1
    return {"labels": ["0", "1", "2", "3", "4", "5"], "counts": counts}


def time_of_day() -> dict:
    """Histogram of word additions by hour of day (UTC)."""
    counts = [0] * 24
    for w in load_words():
        raw = w.last_modified
        if not raw:
            continue
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        counts[d.hour] += 1
    return {"labels": [f"{h:02d}" for h in range(24)], "counts": counts}
