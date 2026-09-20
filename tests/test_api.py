"""Tests for HTTP endpoints in api.py using a real CSV on tmp_path."""

import pytest
from fastapi.testclient import TestClient

from app import cefr, config, data_manager, settings
from app.main import app
from app.models import WordEntry

FIELDS = list(WordEntry.__dataclass_fields__.keys())


def _row(**kwargs):
    return ",".join(f'"{kwargs.get(f, "")}"' for f in FIELDS)


def _write_csv(path, words):
    body = (
        "Your words (csv format)\n\n"
        + ",".join(f'"{f}"' for f in FIELDS)
        + "\n"
        + "".join(_row(**w) + "\n" for w in words)
    )
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = _write_csv(
        tmp_path / "data.txt",
        [
            {"word": "diary", "language": "en", "translation": "дневник", "contexts": "I keep a diary."},
            {"word": "today", "language": "en", "translation": "сегодня", "contexts": "today was so good"},
        ],
    )
    monkeypatch.setattr(data_manager, "CSV_PATH", path)
    return TestClient(app), path


def test_list_words_returns_all_rows(client):
    c, _ = client
    r = c.get("/api/words")
    assert r.status_code == 200
    data = r.json()
    assert [w["word"] for w in data] == ["diary", "today"]
    assert data[0]["translation"] == "дневник"


def test_patch_translation_only(client):
    c, path = client
    r = c.patch("/api/words/0", json={"translation": "записная книжка"})
    assert r.status_code == 200
    assert r.json()["word"]["translation"] == "записная книжка"
    reloaded = data_manager.load_words()
    assert reloaded[0].translation == "записная книжка"


def test_patch_contexts_only(client):
    c, _ = client
    r = c.patch("/api/words/1", json={"contexts": "today is fine"})
    assert r.status_code == 200
    assert r.json()["word"]["contexts"] == "today is fine"


def test_patch_index_out_of_range(client):
    c, _ = client
    r = c.patch("/api/words/99", json={"translation": "x"})
    assert r.status_code == 404


def test_patch_word_to_empty_returns_400(client):
    c, _ = client
    r = c.patch("/api/words/0", json={"word": "   "})
    assert r.status_code == 400


def test_patch_word_not_in_contexts_returns_400(client):
    c, _ = client
    r = c.patch("/api/words/0", json={"word": "journal"})
    assert r.status_code == 400
    assert "contexts" in r.json()["detail"].lower()


def test_patch_word_and_contexts_together_succeeds(client):
    c, _ = client
    r = c.patch(
        "/api/words/0",
        json={
            "word": "journal",
            "contexts": "I keep a journal.",
        },
    )
    assert r.status_code == 200
    assert r.json()["word"]["word"] == "journal"
    assert "journal" in r.json()["word"]["contexts"]


def test_patch_word_matches_context_case_insensitive(client):
    c, _ = client
    r = c.patch(
        "/api/words/0",
        json={
            "word": "DIARY",
            "contexts": "I keep a diary.",
        },
    )
    assert r.status_code == 200


def test_patch_duplicate_word_returns_409(client):
    c, _ = client
    r = c.patch(
        "/api/words/0",
        json={
            "word": "today",
            "contexts": "I keep a diary. today",
        },
    )
    assert r.status_code == 409
    assert "duplicate" in r.json()["detail"].lower()


def test_patch_same_word_same_row_is_not_duplicate(client):
    c, _ = client
    r = c.patch("/api/words/0", json={"word": "diary"})
    assert r.status_code == 200


def test_patch_persists_to_disk(client):
    c, path = client
    c.patch("/api/words/1", json={"translation": "новое"})
    assert '"новое"' in path.read_text(encoding="utf-8")


def test_stats_overview_endpoint(client):
    c, _ = client
    r = c.get("/api/stats/overview")
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_stats_srs_endpoint(client):
    c, _ = client
    r = c.get("/api/stats/srs?days=30")
    assert r.status_code == 200
    assert "days" in r.json() and "counts" in r.json()


def test_stats_difficult_endpoint(client):
    c, _ = client
    r = c.get("/api/stats/difficult?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_stats_velocity_endpoint(client):
    c, _ = client
    r = c.get("/api/stats/velocity")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"days", "added", "cumulative"}


@pytest.mark.parametrize(
    "path,expected_keys",
    [
        ("/api/stats/easiness-histogram", {"labels", "counts"}),
        ("/api/stats/scatter", None),
        ("/api/stats/due-soon?days=1", None),
        ("/api/stats/streak", {"current", "longest", "last"}),
        ("/api/stats/heatmap?days=7", {"days", "start", "end"}),
        ("/api/stats/weekly?weeks=4", {"weeks", "counts"}),
        ("/api/stats/overdue", None),
        ("/api/stats/avg-load?days=7", {"avg", "peak", "days"}),
        ("/api/stats/cefr-profile", {"labels", "counts", "unknown"}),
        ("/api/stats/cefr-avg", {"avg", "matched"}),
        ("/api/stats/cefr-by-easiness", None),
        ("/api/stats/avg-cost", {"avg", "count"}),
        ("/api/stats/next-year-heatmap?days=7", {"days", "start", "end"}),
        ("/api/stats/interval-distribution", {"labels", "counts"}),
        ("/api/stats/recall-ease", {"labels", "counts"}),
        ("/api/stats/time-of-day", {"labels", "counts"}),
    ],
)
def test_stats_endpoint_returns_200(client, path, expected_keys):
    c, _ = client
    r = c.get(path)
    assert r.status_code == 200
    if expected_keys is not None:
        assert set(r.json().keys()) == expected_keys


def test_file_info_existing_file(client):
    c, _ = client
    r = c.get("/api/file-info")
    assert r.status_code == 200
    body = r.json()
    assert body["exists"] is True
    assert body["words"] == 2
    assert body["size_bytes"] > 0
    assert body["size_human"].endswith(("B", "KB", "MB", "GB"))


def test_file_info_missing_file(client, monkeypatch, tmp_path):
    c, _ = client
    missing = tmp_path / "nope.txt"
    monkeypatch.setattr(config, "CSV_PATH", missing)
    r = c.get("/api/file-info")
    assert r.status_code == 200
    assert r.json() == {"exists": False, "path": str(missing)}


def test_get_settings_returns_defaults(client, monkeypatch, tmp_path):
    c, _ = client
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_cache", None)
    r = c.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"mature_days", "young_days"}


def test_patch_settings_persists(client, monkeypatch, tmp_path):
    c, _ = client
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    monkeypatch.setattr(settings, "_cache", None)
    r = c.patch("/api/settings", json={"mature_days": 30, "young_days": 2})
    assert r.status_code == 200
    assert r.json()["mature_days"] == 30
    assert path.exists()


def test_patch_settings_clamps_to_one(client, monkeypatch, tmp_path):
    c, _ = client
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_cache", None)
    r = c.patch("/api/settings", json={"mature_days": 0, "young_days": -5})
    assert r.status_code == 200
    assert r.json()["mature_days"] == 1
    assert r.json()["young_days"] == 1


def test_cefr_reload_reads_temp_dataset(client, monkeypatch, tmp_path):
    c, _ = client
    fake = tmp_path / "cefr.csv"
    fake.write_text("word,cefr\ncat,A1\ndog,B2\n", encoding="utf-8")
    monkeypatch.setattr(config, "CEFR_PATH", fake)
    cefr.load_levels.cache_clear()
    r = c.post("/api/cefr/reload")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "words": 2}
    cefr.load_levels.cache_clear()


def test_bulk_applies_valid_patches(client):
    c, _ = client
    r = c.post(
        "/api/words/bulk",
        json=[
            {"word": "diary", "translation": "новый перевод"},
            {"word": "today", "translation": "сегодня!"},
        ],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["applied"] == 2
    assert body["total"] == 2
    assert body["backup"] is not None


def test_bulk_no_changes_skips_backup(client):
    c, _ = client
    r = c.post("/api/words/bulk", json=[{"word": "missing", "translation": "x"}])
    body = r.json()
    assert body["applied"] == 0
    assert body["backup"] is None
    assert body["results"][0]["ok"] is False
    assert body["results"][0]["error"] == "not found"


def test_bulk_rejects_empty_new_word(client):
    c, _ = client
    r = c.post("/api/words/bulk", json=[{"word": "diary", "new_word": "   "}])
    body = r.json()
    assert body["applied"] == 0
    assert body["results"][0]["error"] == "empty new_word"


def test_bulk_rejects_new_word_not_in_contexts(client):
    c, _ = client
    r = c.post("/api/words/bulk", json=[{"word": "diary", "new_word": "journal"}])
    body = r.json()
    assert body["applied"] == 0
    assert body["results"][0]["error"] == "new word not in contexts"


def test_bulk_rejects_duplicate_with_existing(client):
    c, _ = client
    r = c.post(
        "/api/words/bulk",
        json=[
            {"word": "diary", "new_word": "today", "contexts": "today is in diary"},
        ],
    )
    body = r.json()
    assert body["applied"] == 0
    assert body["results"][0]["error"] == "duplicate"


def test_bulk_rejects_duplicate_within_batch(client):
    c, _ = client
    r = c.post(
        "/api/words/bulk",
        json=[
            {"word": "diary", "new_word": "journal", "contexts": "I keep a journal."},
            {"word": "today", "new_word": "JOURNAL", "contexts": "journal is my favorite word"},
        ],
    )
    body = r.json()
    assert body["applied"] == 1
    assert body["results"][1]["error"] == "duplicate in batch"


def test_bulk_rename_persists(client):
    c, _ = client
    r = c.post(
        "/api/words/bulk",
        json=[
            {"word": "diary", "new_word": "journal", "contexts": "I keep a journal."},
        ],
    )
    assert r.status_code == 200
    assert r.json()["applied"] == 1
    words = data_manager.load_words()
    assert words[0].word == "journal"
