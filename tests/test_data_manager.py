"""Tests for CSV read/write round-trip in data_manager."""

import csv
import io

import pytest

from app import data_manager
from app.models import WordEntry

FIELDS = list(WordEntry.__dataclass_fields__.keys())


def _csv_rows(rows):
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def _write_file(path, words=None, with_extra=True):
    """Build a Readlang-shaped file. Keep sections minimal but realistic."""
    parts = []
    if with_extra:
        parts.append("Personal data (csv format)\n")
        parts.append(_csv_rows([["user_id", "username"], ["123", "alex"]]))
        parts.append("\n")
    parts.append("Your words (csv format)\n\n")
    parts.append(_csv_rows([FIELDS] + [[w.get(f, "") for f in FIELDS] for w in (words or [])]))
    if with_extra:
        parts.append("\nOther section (csv format)\n")
        parts.append(_csv_rows([["a", "b"], ["1", "2"]]))
    path.write_bytes("".join(parts).encode("utf-8"))
    return path


@pytest.fixture
def sample(tmp_path, monkeypatch):
    path = _write_file(
        tmp_path / "sample.txt",
        words=[
            {"word": "diary", "language": "en", "translation": "дневник"},
        ],
    )
    monkeypatch.setattr(data_manager, "CSV_PATH", path)
    return path


def test_read_lines_preserves_line_endings(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"a\nb\r\nc")
    assert data_manager._read_lines(f) == ["a\n", "b\r\n", "c"]


def test_load_words_returns_dataclass_instances(sample):
    words = data_manager.load_words()
    assert len(words) == 1
    assert isinstance(words[0], WordEntry)
    assert words[0].word == "diary"
    assert words[0].translation == "дневник"


def test_load_words_empty_section(tmp_path, monkeypatch):
    path = _write_file(tmp_path / "empty.txt", words=[])
    monkeypatch.setattr(data_manager, "CSV_PATH", path)
    assert data_manager.load_words() == []


def test_load_words_skips_rows_without_word(tmp_path, monkeypatch):
    path = _write_file(
        tmp_path / "some.txt",
        words=[
            {"word": "diary", "translation": "дневник"},
            {"word": "", "translation": "пусто"},
            {"word": "today", "translation": "сегодня"},
        ],
    )
    monkeypatch.setattr(data_manager, "CSV_PATH", path)
    assert [w.word for w in data_manager.load_words()] == ["diary", "today"]


def test_load_words_fills_missing_fields_with_empty_string(tmp_path, monkeypatch):
    path = tmp_path / "partial.txt"
    path.write_text(
        'Your words (csv format)\n\n"word","language"\n"solo","en"\n\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(data_manager, "CSV_PATH", path)
    words = data_manager.load_words()
    assert len(words) == 1
    assert words[0].word == "solo"
    assert words[0].translation == ""
    assert words[0].relevancy == ""


def test_find_words_bounds_returns_header_and_next_section():
    lines = [
        "Personal data (csv format)\n",
        '"a","b"\n',
        "\n",
        "Your words (csv format)\n",
        "\n",
        '"word","language"\n',
        '"diary","en"\n',
        "\n",
        "Other (csv format)\n",
        '"x","y"\n',
    ]
    start, end = data_manager._find_words_bounds(lines)
    assert lines[start].lstrip().startswith('"word"')
    assert lines[end] == "Other (csv format)\n"


def test_find_words_bounds_raises_when_marker_missing():
    lines = ["Personal data (csv format)\n", '"a","b"\n']
    with pytest.raises(StopIteration):
        data_manager._find_words_bounds(lines)


def test_save_preserves_other_sections_and_tail(sample):
    original = sample.read_text(encoding="utf-8")
    tail_marker = "Other section (csv format)"
    original_tail = original[original.index(tail_marker) :]

    words = data_manager.load_words()
    words[0].translation = "изменено"
    data_manager.save_words(words)

    after = sample.read_text(encoding="utf-8")
    assert "Personal data (csv format)" in after
    assert '"user_id","username"' in after
    assert after.endswith(original_tail)
    assert '"изменено"' in after
    assert '"дневник"' not in after


def test_save_then_load_roundtrip(sample):
    original = data_manager.load_words()
    data_manager.save_words(original)
    reloaded = data_manager.load_words()
    assert reloaded == original


def test_save_then_load_roundtrip_with_multiline_context(tmp_path, monkeypatch):
    path = _write_file(
        tmp_path / "ctx.txt",
        words=[
            {
                "word": "even",
                "language": "en",
                "translation": "даже",
                "contexts": 'first line|second line with, comma and "quotes"',
            },
        ],
    )
    monkeypatch.setattr(data_manager, "CSV_PATH", path)

    original = data_manager.load_words()
    assert original[0].contexts == 'first line|second line with, comma and "quotes"'

    data_manager.save_words(original)
    reloaded = data_manager.load_words()
    assert reloaded == original
