"""Sanity checks on config paths — they must point inside the project."""

from pathlib import Path

from app import config


def test_base_dir_is_project_root():
    assert (config.BASE_DIR / "app").is_dir()
    assert (config.BASE_DIR / "main.py").is_file()


def test_paths_are_absolute_and_nested():
    for p in (config.CSV_PATH, config.WEB_DIR, config.STATIC_DIR):
        assert isinstance(p, Path)
        assert p.is_absolute()
        assert config.BASE_DIR in p.parents


def test_host_and_port_types():
    assert isinstance(config.HOST, str)
    assert isinstance(config.PORT, int)
    assert 1024 < config.PORT < 65536


def test_debug_is_bool():
    assert isinstance(config.DEBUG, bool)
