"""Tests for CEFR level lookup in cefr.py."""

import pytest

from app import cefr, config


@pytest.fixture(autouse=True)
def _reset_cache():
    """load_levels is lru_cached; reset around every test for isolation."""
    cefr.load_levels.cache_clear()
    yield
    cefr.load_levels.cache_clear()


@pytest.fixture
def cefr_file(monkeypatch, tmp_path):
    """Point config.CEFR_PATH at a temp CSV with the given content."""

    def _write(text):
        path = tmp_path / "cefr.csv"
        path.write_text(text, encoding="utf-8")
        monkeypatch.setattr(config, "CEFR_PATH", path)

    return _write


def test_load_levels_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CEFR_PATH", tmp_path / "nope.csv")
    assert cefr.load_levels() == {}


def test_load_levels_basic(cefr_file):
    cefr_file("word,cefr\ncat,A1\nDog,B2\n")
    assert cefr.load_levels() == {"cat": "A1", "dog": "B2"}


def test_load_levels_case_insensitive_columns(cefr_file):
    cefr_file("WORD,CeFr\ncat,A1\n")
    assert cefr.load_levels() == {"cat": "A1"}


@pytest.mark.parametrize("word_col", ["headword", "term", "lemma"])
def test_load_levels_alternative_word_columns(cefr_file, word_col):
    cefr_file(f"{word_col},cefr\ncat,A1\n")
    assert cefr.load_levels() == {"cat": "A1"}


@pytest.mark.parametrize("level_col", ["cefr_level", "level"])
def test_load_levels_alternative_level_columns(cefr_file, level_col):
    cefr_file(f"word,{level_col}\ncat,A1\n")
    assert cefr.load_levels() == {"cat": "A1"}


def test_load_levels_missing_columns_returns_empty(cefr_file):
    cefr_file("foo,bar\ncat,A1\n")
    assert cefr.load_levels() == {}


def test_load_levels_skips_invalid_rows(cefr_file):
    cefr_file("word,cefr\ncat,A1\n,X2\nX2,B2\ndog,\n")
    assert cefr.load_levels() == {"cat": "A1", "x2": "B2"}


def test_find_col_missing_returns_none():
    assert cefr._find_col(["a", "b"], ("word",)) is None


def test_find_col_case_insensitive():
    assert cefr._find_col(["Word"], ("word",)) == "Word"


def test_find_col_handles_none_fieldnames():
    assert cefr._find_col(None, ("word",)) is None


@pytest.mark.parametrize(
    "word,expected",
    [
        ("cities", ["city", "citi", "citie"]),
        ("boxes", ["box", "boxe"]),
        ("cats", ["cat"]),
        ("class", []),
        ("running", ["runn", "runne"]),
        ("played", ["play", "playe"]),
        ("a", []),
    ],
)
def test_stem_candidates(word, expected):
    assert cefr._stem_candidates(word) == expected


def test_lookup_one_empty_returns_none(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr._lookup_one("   ") is None


def test_lookup_one_direct_hit(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr._lookup_one("CAT") == "A1"


def test_lookup_one_via_stem(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr._lookup_one("cats") == "A1"


def test_get_level_empty_and_none(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr.get_level("") is None
    assert cefr.get_level(None) is None


def test_get_level_single_word(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr.get_level("cat") == "A1"


def test_get_level_phrase_returns_highest(cefr_file):
    cefr_file("word,cefr\ncat,A1\ndog,B2\n")
    assert cefr.get_level("cat dog") == "B2"


def test_get_level_phrase_no_matches(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr.get_level("xyz abc") is None


def test_get_level_num_known(cefr_file):
    cefr_file("word,cefr\ncat,B1\n")
    assert cefr.get_level_num("cat") == 3


def test_get_level_num_unknown(cefr_file):
    cefr_file("word,cefr\ncat,A1\n")
    assert cefr.get_level_num("zzz") is None
