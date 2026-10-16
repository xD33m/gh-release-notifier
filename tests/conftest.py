"""Shared fixtures.

Every test gets its own SQLite file and a fixed in-memory configuration, so
nothing touches /app/data, the real config.yaml or the network.
"""

import asyncio

import pytest

from app import config as config_module
from app import database
from app.config import AppConfig


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    path = tmp_path / "releases.db"
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    asyncio.run(database.init_db())
    return path


@pytest.fixture
def set_config(monkeypatch):
    """Replace the global configuration for the duration of a test."""

    def _set(**values):
        cfg = AppConfig(**values)
        monkeypatch.setattr(config_module._config_manager, "_config", cfg)
        return cfg

    return _set


@pytest.fixture(autouse=True)
def default_config(set_config):
    return set_config()
