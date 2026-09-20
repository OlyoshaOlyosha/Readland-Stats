"""Tests for the WordEntry dataclass contract."""

from app.models import WordEntry


def test_defaults_are_empty_strings():
    w = WordEntry()
    for field in WordEntry.__dataclass_fields__:
        assert getattr(w, field) == ""


def test_construction_with_partial_kwargs():
    w = WordEntry(word="diary", translation="дневник")
    assert w.word == "diary"
    assert w.translation == "дневник"
    assert w.language == ""


def test_field_order_matches_csv_header():
    expected = [
        "word",
        "language",
        "translation",
        "contexts",
        "last_modified",
        "alternatives",
        "spaced_repetition_next_date",
        "spaced_repetition_interval",
        "spaced_repetition_easiness_factor",
        "spaced_repetition_recall_attempts",
        "spaced_repetition_last_recall_ease",
        "spaced_repetition_previous_interval",
        "spaced_repetition_previous_interval_date",
        "deleted_date",
        "favorite",
        "relevancy",
    ]
    assert list(WordEntry.__dataclass_fields__.keys()) == expected


def test_equality_by_value():
    a = WordEntry(word="x", translation="y")
    b = WordEntry(word="x", translation="y")
    assert a == b


def test_inequality_when_field_differs():
    a = WordEntry(word="x")
    b = WordEntry(word="y")
    assert a != b
