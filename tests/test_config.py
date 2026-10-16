"""Configuration: config.yaml values plus secrets from the environment."""

import pytest

from app.config import ConfigManager

ENV_VARS = (
    "GITHUB_TOKEN",
    "CHECK_INTERVAL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "DISCORD_WEBHOOK_URL",
)


@pytest.fixture
def load(tmp_path, monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def _load(yaml_text="", **env):
        path = tmp_path / "config.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        monkeypatch.setattr(ConfigManager, "_get_config_path", lambda self: path)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return ConfigManager().config

    return _load


def test_defaults_without_file_content(load):
    cfg = load()
    assert cfg.check_interval == 30
    assert cfg.repositories == []
    assert not cfg.notifications.telegram.enabled
    assert not cfg.notifications.discord.enabled


def test_yaml_values_are_read(load):
    cfg = load("check_interval: 5\nrepositories:\n  - acme/widget\n")
    assert cfg.check_interval == 5
    assert cfg.repositories == ["acme/widget"]


def test_environment_overrides_yaml(load):
    cfg = load("check_interval: 5\n", CHECK_INTERVAL="60", GITHUB_TOKEN="token-from-env")
    assert cfg.check_interval == 60
    assert cfg.github_token == "token-from-env"


def test_telegram_enabled_only_with_token_and_chat_id(load):
    assert not load(TELEGRAM_BOT_TOKEN="123:abc").notifications.telegram.enabled

    cfg = load(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_CHAT_ID="42")
    assert cfg.notifications.telegram.enabled
    assert cfg.notifications.telegram.chat_id == "42"


def test_discord_webhook_enables_discord(load):
    cfg = load(DISCORD_WEBHOOK_URL="https://discord.example/webhook")
    assert cfg.notifications.discord.enabled
    assert cfg.notifications.discord.webhook_url == "https://discord.example/webhook"


def test_explicit_disable_in_yaml_wins_over_env(load):
    yaml_text = "notifications:\n  discord:\n    enabled: false\n  telegram:\n    enabled: false\n"
    cfg = load(
        yaml_text,
        DISCORD_WEBHOOK_URL="https://discord.example/webhook",
        TELEGRAM_BOT_TOKEN="123:abc",
        TELEGRAM_CHAT_ID="42",
    )
    assert not cfg.notifications.discord.enabled
    assert not cfg.notifications.telegram.enabled
