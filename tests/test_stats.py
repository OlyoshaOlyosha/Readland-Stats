"""Tests for analytics computations in stats."""

import pytest
from freezegun import freeze_time

from app import stats
from app.models import WordEntry

MS_PER_DAY = 86_400_000


def _w(**kwargs):
    """Build a WordEntry with only the fields we care about."""
    return WordEntry(**kwargs)


@pytest.fixture
def patch_words(monkeypatch):
    """Replace load_words in stats with a controlled list."""

    def _apply(words):
        monkeypatch.setattr(stats, "load_words", lambda: list(words))

    return _apply


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("3", 3),
        ("3.9", 3),
        (None, 0),
        ("", 0),
        ("abc", 0),
        (7, 7),
        (2.5, 2),
    ],
)
def test_to_int(raw, expected):
    assert stats._to_int(raw) == expected


def test_days_from_ms():
    assert stats._days_from_ms(str(3 * MS_PER_DAY)) == 3.0
    assert stats._days_from_ms("") == 0.0
    assert stats._days_from_ms(None) == 0.0


@pytest.mark.parametrize(
    "interval_ms,expected",
    [
        (str(21 * MS_PER_DAY), "mature"),
        (str(22 * MS_PER_DAY), "mature"),
        (str(1 * MS_PER_DAY), "young"),
        (str(20 * MS_PER_DAY), "young"),
        ("1000", "learning"),
        ("0", "learning"),
        ("", "new"),
        (None, "new"),
    ],
)
def test_status_classifies_interval(interval_ms, expected):
    w = _w(spaced_repetition_interval=interval_ms)
    assert stats._status(w, mature_days=21, young_days=1) == expected


def test_overview_counts_and_averages(patch_words):
    patch_words([
        _w(
            spaced_repetition_interval=str(21 * MS_PER_DAY),
            spaced_repetition_easiness_factor="2.5",
            spaced_repetition_recall_attempts="3",
        ),
        _w(
            spaced_repetition_interval=str(5 * MS_PER_DAY),
            spaced_repetition_easiness_factor="2.0",
            spaced_repetition_recall_attempts="5",
        ),
        _w(spaced_repetition_interval="", spaced_repetition_easiness_factor="", spaced_repetition_recall_attempts=""),
    ])
    s = stats.overview()
    assert s["total"] == 3
    assert s["by_status"] == {"mature": 1, "young": 1, "new": 1}
    assert s["avg_easiness"] == 2.25
    assert s["total_attempts"] == 8
    assert s["mature_share"] == pytest.approx(33.3, abs=0.1)


def test_overview_empty_list(patch_words):
    patch_words([])
    s = stats.overview()
    assert s["total"] == 0
    assert s["by_status"] == {}
    assert s["avg_easiness"] == 0
    assert s["total_attempts"] == 0
    assert s["mature_share"] == 0


def test_overview_ignores_undefined_easiness(patch_words):
    patch_words([
        _w(spaced_repetition_easiness_factor="undefined"),
        _w(spaced_repetition_easiness_factor="2.0"),
    ])
    s = stats.overview()
    assert s["avg_easiness"] == 2.0


@freeze_time("2026-01-15")
def test_srs_calendar_buckets_by_day(patch_words):
    patch_words([
        _w(spaced_repetition_next_date="2026-01-15T10:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-15T22:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-17T09:00:00Z"),
    ])
    result = stats.srs_calendar(days_ahead=10)
    assert result["days"] == ["2026-01-15", "2026-01-17"]
    assert result["counts"] == [2, 1]


@freeze_time("2026-01-15")
def test_srs_calendar_skips_past_and_far_future(patch_words):
    patch_words([
        _w(spaced_repetition_next_date="2026-01-14T23:59:00Z"),
        _w(spaced_repetition_next_date="2026-01-16T00:00:00Z"),
        _w(spaced_repetition_next_date="2027-01-01T00:00:00Z"),
    ])
    result = stats.srs_calendar(days_ahead=5)
    assert result["days"] == ["2026-01-16"]
    assert result["counts"] == [1]


@freeze_time("2026-01-15")
def test_srs_calendar_skips_invalid_and_undefined(patch_words):
    patch_words([
        _w(spaced_repetition_next_date="undefined"),
        _w(spaced_repetition_next_date=""),
        _w(spaced_repetition_next_date="not-a-date"),
        _w(spaced_repetition_next_date="2026-01-16T00:00:00Z"),
    ])
    result = stats.srs_calendar(days_ahead=10)
    assert result["days"] == ["2026-01-16"]
    assert result["counts"] == [1]


def test_difficult_words_sorts_by_score_and_skips_zero_attempts(patch_words):
    patch_words([
        _w(
            word="easy",
            translation="легко",
            spaced_repetition_recall_attempts="2",
            spaced_repetition_easiness_factor="2.5",
        ),
        _w(
            word="hard",
            translation="тяжело",
            spaced_repetition_recall_attempts="10",
            spaced_repetition_easiness_factor="1.5",
        ),
        _w(
            word="untouched",
            translation="нетронутое",
            spaced_repetition_recall_attempts="0",
            spaced_repetition_easiness_factor="2.5",
        ),
    ])
    rows = stats.difficult_words(limit=10)
    assert [r["word"] for r in rows] == ["hard", "easy"]
    assert rows[0]["score"] > rows[1]["score"]


def test_difficult_words_uses_default_easiness_when_missing(patch_words):
    patch_words([
        _w(word="x", spaced_repetition_recall_attempts="5", spaced_repetition_easiness_factor="undefined"),
    ])
    rows = stats.difficult_words()
    assert rows[0]["easiness"] == 2.5
    assert rows[0]["score"] == pytest.approx(5 / 2.5)


def test_difficult_words_respects_limit(patch_words):
    patch_words([
        _w(word=f"w{i}", spaced_repetition_recall_attempts=str(i), spaced_repetition_easiness_factor="2.5")
        for i in range(1, 21)
    ])
    assert len(stats.difficult_words(limit=5)) == 5


def test_velocity_groups_by_day_and_accumulates(patch_words):
    patch_words([
        _w(last_modified="2026-01-10T10:00:00Z"),
        _w(last_modified="2026-01-10T18:00:00Z"),
        _w(last_modified="2026-01-12T09:00:00Z"),
    ])
    v = stats.velocity()
    assert v["days"] == ["2026-01-10", "2026-01-12"]
    assert v["added"] == [2, 1]
    assert v["cumulative"] == [2, 3]


def test_velocity_skips_invalid_dates(patch_words):
    patch_words([
        _w(last_modified=""),
        _w(last_modified="garbage"),
        _w(last_modified="2026-01-10T10:00:00Z"),
    ])
    v = stats.velocity()
    assert v["days"] == ["2026-01-10"]
    assert v["cumulative"] == [1]


def test_velocity_empty(patch_words):
    patch_words([])
    v = stats.velocity()
    assert v == {"days": [], "added": [], "cumulative": []}


def test_easiness_histogram_buckets(patch_words):
    patch_words([
        _w(spaced_repetition_easiness_factor="1.4"),
        _w(spaced_repetition_easiness_factor="1.6"),
        _w(spaced_repetition_easiness_factor="2.5"),
        _w(spaced_repetition_easiness_factor="3.0"),
        _w(spaced_repetition_easiness_factor="undefined"),
        _w(spaced_repetition_easiness_factor="bad"),
    ])
    h = stats.easiness_histogram()
    assert h["labels"] == ["< 1.5", "1.5-1.8", "1.8-2.1", "2.1-2.4", "2.4-2.7", ">= 2.7"]
    assert h["counts"] == [1, 1, 0, 0, 1, 1]


def test_easiness_histogram_empty(patch_words):
    patch_words([])
    assert stats.easiness_histogram()["counts"] == [0, 0, 0, 0, 0, 0]


def test_scatter_data_skips_zero_attempts(patch_words, monkeypatch):
    monkeypatch.setattr(stats, "get_level", lambda w: None)
    patch_words([
        _w(
            word="cat",
            translation="кот",
            contexts="the cat sat|extra",
            spaced_repetition_recall_attempts="3",
            spaced_repetition_easiness_factor="2.0",
            spaced_repetition_interval=str(21 * MS_PER_DAY),
        ),
        _w(
            word="hello world",
            translation="привет",
            contexts="",
            spaced_repetition_recall_attempts="2",
            spaced_repetition_easiness_factor="undefined",
        ),
        _w(word="untouched", spaced_repetition_recall_attempts="0"),
    ])
    rows = stats.scatter_data()
    assert len(rows) == 2
    cat = next(r for r in rows if r["word"] == "cat")
    assert cat["attempts"] == 3
    assert cat["easiness"] == 2.0
    assert cat["is_phrase"] is False
    assert cat["word_length"] == 1
    assert cat["context_length"] == len("the cat sat")
    assert cat["status"] == "mature"
    hw = next(r for r in rows if r["word"] == "hello world")
    assert hw["easiness"] == 2.5
    assert hw["is_phrase"] is True
    assert hw["word_length"] == 2
    assert hw["context_length"] == 0


@freeze_time("2026-01-15")
def test_due_soon_includes_today_and_tomorrow(patch_words):
    patch_words([
        _w(word="b", spaced_repetition_next_date="2026-01-16T10:00:00Z"),
        _w(word="a", spaced_repetition_next_date="2026-01-15T09:00:00Z"),
        _w(word="c", spaced_repetition_next_date="2026-01-20T09:00:00Z"),
        _w(word="d", spaced_repetition_next_date="2026-01-14T09:00:00Z"),
        _w(word="e", spaced_repetition_next_date="undefined"),
    ])
    rows = stats.due_soon(days=1)
    assert [r["word"] for r in rows] == ["a", "b"]
    assert rows[0]["days"] == 0
    assert rows[1]["days"] == 1


@freeze_time("2026-01-15")
def test_streak_current_and_longest(patch_words):
    patch_words([
        _w(last_modified="2026-01-10T10:00:00Z"),
        _w(last_modified="2026-01-11T10:00:00Z"),
        _w(last_modified="2026-01-12T10:00:00Z"),
        _w(last_modified="2026-01-14T10:00:00Z"),
        _w(last_modified="2026-01-15T10:00:00Z"),
    ])
    s = stats.streak()
    assert s["longest"] == 3
    assert s["current"] == 2
    assert s["last"] == "2026-01-15"


def test_streak_empty(patch_words):
    patch_words([])
    assert stats.streak() == {"current": 0, "longest": 0, "last": None}


@freeze_time("2026-01-15")
def test_heatmap_continuous_range(patch_words):
    patch_words([
        _w(last_modified="2026-01-15T10:00:00Z"),
        _w(last_modified="2026-01-15T18:00:00Z"),
        _w(last_modified="2026-01-13T10:00:00Z"),
    ])
    h = stats.heatmap(days=3)
    assert h["start"] == "2026-01-13"
    assert h["end"] == "2026-01-15"
    assert h["days"] == [
        {"date": "2026-01-13", "count": 1},
        {"date": "2026-01-14", "count": 0},
        {"date": "2026-01-15", "count": 2},
    ]


def test_weekly_added_groups_and_limits(patch_words):
    patch_words([
        _w(last_modified="2025-12-29T10:00:00Z"),
        _w(last_modified="2026-01-05T10:00:00Z"),
        _w(last_modified="2026-01-06T10:00:00Z"),
        _w(last_modified="2026-01-12T10:00:00Z"),
    ])
    r = stats.weekly_added(weeks=2)
    assert r["weeks"] == ["2026-W02", "2026-W03"]
    assert r["counts"] == [2, 1]


def test_weekly_added_skips_invalid(patch_words):
    patch_words([_w(last_modified="garbage"), _w(last_modified="")])
    assert stats.weekly_added() == {"weeks": [], "counts": []}


@freeze_time("2026-01-15")
def test_overdue_sorted_by_days_desc(patch_words):
    patch_words([
        _w(word="a", spaced_repetition_next_date="2026-01-14T10:00:00Z"),
        _w(word="b", spaced_repetition_next_date="2026-01-01T10:00:00Z"),
        _w(word="c", spaced_repetition_next_date="2026-01-15T10:00:00Z"),
        _w(word="d", spaced_repetition_next_date="undefined"),
    ])
    rows = stats.overdue()
    assert [r["word"] for r in rows] == ["b", "a"]
    assert rows[0]["overdue_days"] == 14
    assert rows[1]["overdue_days"] == 1


@freeze_time("2026-01-15")
def test_avg_load_avg_and_peak(patch_words):
    patch_words([
        _w(spaced_repetition_next_date="2026-01-15T10:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-16T10:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-16T11:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-17T10:00:00Z"),
    ])
    r = stats.avg_load(days=5)
    assert r["peak"] == 2
    assert r["avg"] == round(4 / 3, 1)
    assert r["days"] == 5


def test_avg_load_empty(patch_words):
    patch_words([])
    assert stats.avg_load() == {"avg": 0, "peak": 0, "days": 30}


def test_cefr_profile_counts_and_unknown(patch_words, monkeypatch):
    monkeypatch.setattr(stats, "get_level", lambda w: {"cat": "A1", "dog": "B2"}.get(w))
    patch_words([_w(word="cat"), _w(word="dog"), _w(word="xyz")])
    r = stats.cefr_profile()
    assert r["labels"] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert r["counts"] == [1, 0, 0, 1, 0, 0]
    assert r["unknown"] == 1


def test_cefr_avg_matched_and_avg(patch_words, monkeypatch):
    monkeypatch.setattr(stats, "get_level_num", lambda w: {"a": 2, "b": 4}.get(w))
    patch_words([_w(word="a"), _w(word="b"), _w(word="z")])
    assert stats.cefr_avg() == {"avg": 3.0, "matched": 2}


def test_cefr_avg_no_matches(patch_words, monkeypatch):
    monkeypatch.setattr(stats, "get_level_num", lambda w: None)
    patch_words([_w(word="a")])
    assert stats.cefr_avg() == {"avg": 0, "matched": 0}


def test_cefr_by_easiness_aggregates(patch_words, monkeypatch):
    monkeypatch.setattr(stats, "get_level", lambda w: {"a": "A1", "b": "A1", "c": "B1"}.get(w))
    patch_words([
        _w(word="a", spaced_repetition_easiness_factor="2.0"),
        _w(word="b", spaced_repetition_easiness_factor="3.0"),
        _w(word="c", spaced_repetition_easiness_factor="2.5"),
        _w(word="d", spaced_repetition_easiness_factor="undefined"),
    ])
    rows = stats.cefr_by_easiness()
    assert len(rows) == 6
    a1 = next(r for r in rows if r["level"] == "A1")
    assert a1["avg_easiness"] == 2.5
    assert a1["count"] == 2
    b1 = next(r for r in rows if r["level"] == "B1")
    assert b1["avg_easiness"] == 2.5
    assert b1["count"] == 1


def test_avg_cost_only_mature_with_attempts(patch_words, monkeypatch):
    monkeypatch.setattr(stats.settings, "load", lambda: {"mature_days": 21, "young_days": 1})
    patch_words([
        _w(spaced_repetition_interval=str(21 * MS_PER_DAY), spaced_repetition_recall_attempts="4"),
        _w(spaced_repetition_interval=str(30 * MS_PER_DAY), spaced_repetition_recall_attempts="6"),
        _w(spaced_repetition_interval=str(30 * MS_PER_DAY), spaced_repetition_recall_attempts="0"),
        _w(spaced_repetition_interval=str(5 * MS_PER_DAY), spaced_repetition_recall_attempts="10"),
    ])
    assert stats.avg_cost() == {"avg": 5.0, "count": 2}


@freeze_time("2026-01-15")
def test_next_year_heatmap_continuous_and_counts(patch_words):
    patch_words([
        _w(spaced_repetition_next_date="2026-01-15T10:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-17T10:00:00Z"),
        _w(spaced_repetition_next_date="2026-01-17T11:00:00Z"),
        _w(spaced_repetition_next_date="2026-02-01T10:00:00Z"),
    ])
    r = stats.next_year_heatmap(days=3)
    assert r["start"] == "2026-01-15"
    assert r["end"] == "2026-01-17"
    assert r["days"] == [
        {"date": "2026-01-15", "count": 1},
        {"date": "2026-01-16", "count": 0},
        {"date": "2026-01-17", "count": 2},
    ]


def test_interval_distribution_buckets(patch_words):
    patch_words([
        _w(spaced_repetition_interval="0"),
        _w(spaced_repetition_interval=str(3 * MS_PER_DAY)),
        _w(spaced_repetition_interval=str(10 * MS_PER_DAY)),
        _w(spaced_repetition_interval=str(50 * MS_PER_DAY)),
        _w(spaced_repetition_interval=str(200 * MS_PER_DAY)),
        _w(spaced_repetition_interval=str(400 * MS_PER_DAY)),
        _w(spaced_repetition_interval=""),
        _w(spaced_repetition_interval="undefined"),
    ])
    r = stats.interval_distribution()
    assert r["labels"] == ["—", "<1", "1-7", "7-30", "30-90", "90-180", "180-365", "365+"]
    assert r["counts"] == [2, 1, 1, 1, 1, 0, 1, 1]


def test_recall_ease_histogram_bounds_and_types(patch_words):
    patch_words([
        _w(spaced_repetition_last_recall_ease="0"),
        _w(spaced_repetition_last_recall_ease="3"),
        _w(spaced_repetition_last_recall_ease="5"),
        _w(spaced_repetition_last_recall_ease="6"),
        _w(spaced_repetition_last_recall_ease="undefined"),
        _w(spaced_repetition_last_recall_ease="bad"),
    ])
    r = stats.recall_ease_histogram()
    assert r["labels"] == ["0", "1", "2", "3", "4", "5"]
    assert r["counts"] == [1, 0, 0, 1, 0, 1]


def test_time_of_day_buckets_by_hour(patch_words):
    patch_words([
        _w(last_modified="2026-01-15T00:30:00Z"),
        _w(last_modified="2026-01-15T10:15:00Z"),
        _w(last_modified="2026-01-15T10:45:00Z"),
        _w(last_modified="2026-01-15T23:00:00Z"),
        _w(last_modified="garbage"),
    ])
    r = stats.time_of_day()
    assert len(r["labels"]) == 24
    assert len(r["counts"]) == 24
    assert r["counts"][0] == 1
    assert r["counts"][10] == 2
    assert r["counts"][23] == 1
    assert sum(r["counts"]) == 4
