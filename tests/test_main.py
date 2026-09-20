"""Smoke tests for the FastAPI app wiring (HTML + static mount)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_returns_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "<!DOCTYPE html>" in r.text
    assert "Readlang Stats" in r.text


def test_static_css_served():
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert ":root" in r.text


def test_static_js_served():
    r = client.get("/static/app.js")
    assert r.status_code == 200
    assert "Chart" in r.text


def test_missing_static_returns_404():
    r = client.get("/static/nonexistent.file")
    assert r.status_code == 404
