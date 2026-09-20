"""Tests for runtime settings in settings.py."""

import json

import pytest

from app import config, settings


@pytest.fixture(autouse=True)
def _reset_cache():
    settings._cache = None
    yield
    settings._cache = None


@pytest.fixture
def settings_path(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    return path


def test_read_missing_file_returns_defaults(settings_path):
    assert settings._read() == {
        "mature_days": config.MATURE_DAYS,
        "young_days": config.YOUNG_DAYS,
    }


def test_read_valid_file_merges_with_defaults(settings_path):
    settings_path.write_text(json.dumps({"mature_days": 30}), encoding="utf-8")
    result = settings._read()
    assert result["mature_days"] == 30
    assert result["young_days"] == config.YOUNG_DAYS


def test_read_broken_json_returns_defaults(settings_path):
    settings_path.write_text("{not json", encoding="utf-8")
    assert settings._read() == {
        "mature_days": config.MATURE_DAYS,
        "young_days": config.YOUNG_DAYS,
    }


def test_read_oserror_returns_defaults(monkeypatch, tmp_path):
    directory = tmp_path / "settings.json"
    directory.mkdir()
    monkeypatch.setattr(settings, "SETTINGS_PATH", directory)
    assert settings._read() == {
        "mature_days": config.MATURE_DAYS,
        "young_days": config.YOUNG_DAYS,
    }


def test_read_ignores_unknown_keys(settings_path):
    settings_path.write_text(json.dumps({"mature_days": 30, "extra": "x"}), encoding="utf-8")
    result = settings._read()
    assert "extra" not in result


def test_load_returns_defaults_first_time(settings_path):
    assert settings.load() == {
        "mature_days": config.MATURE_DAYS,
        "young_days": config.YOUNG_DAYS,
    }


def test_load_caches_after_first_read(settings_path):
    settings_path.write_text(json.dumps({"mature_days": 30}), encoding="utf-8")
    first = settings.load()
    settings_path.write_text(json.dumps({"mature_days": 99}), encoding="utf-8")
    second = settings.load()
    assert first is second
    assert second["mature_days"] == 30


def test_save_writes_file(settings_path):
    result = settings.save({"mature_days": 14, "young_days": 3})
    assert result == {"mature_days": 14, "young_days": 3}
    assert json.loads(settings_path.read_text(encoding="utf-8")) == result


def test_save_clamps_values_to_one(settings_path):
    result = settings.save({"mature_days": 0, "young_days": -5})
    assert result["mature_days"] == 1
    assert result["young_days"] == 1


def test_save_coerces_strings_to_int(settings_path):
    result = settings.save({"mature_days": "30"})
    assert result["mature_days"] == 30


def test_save_ignores_none_values(settings_path):
    result = settings.save({"mature_days": None, "young_days": 5})
    assert result["mature_days"] == config.MATURE_DAYS
    assert result["young_days"] == 5


def test_save_ignores_unknown_keys(settings_path):
    result = settings.save({"mature_days": 30, "unknown": 999})
    assert "unknown" not in result


def test_save_updates_cache(settings_path):
    settings.save({"mature_days": 30})
    assert settings.load()["mature_days"] == 30


def test_save_creates_parent_directory(monkeypatch, tmp_path):
    nested = tmp_path / "a" / "b" / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", nested)
    settings.save({"mature_days": 30})
    assert nested.exists()
