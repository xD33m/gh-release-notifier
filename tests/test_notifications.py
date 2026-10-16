"""Message formatting for Telegram and Discord, with the HTTP call faked out."""

import asyncio

import pytest

from app.notifications import discord, telegram

RELEASE = {
    "owner": "acme",
    "repo_name": "widget",
    "tag_name": "v1.2.0",
    "name": "Widget 1.2",
    "html_url": "https://github.com/acme/widget/releases/tag/v1.2.0",
    "body": "",
}


class FakeResponse:
    def raise_for_status(self):
        return None


@pytest.fixture
def posts(monkeypatch):
    """Record every POST made through httpx.AsyncClient."""
    calls: list[dict] = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, timeout=None):
            calls.append({"url": url, "json": json})
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    return calls


def test_telegram_message_escapes_markdown_and_truncates(posts, set_config):
    set_config(notifications={"telegram": {"enabled": True, "bot_token": "123:abc", "chat_id": "42"}})
    body = "Fixed *bold* and _italic_ in `code`. " + "x" * 600

    assert asyncio.run(telegram.send_telegram_notification(RELEASE | {"body": body}))

    (call,) = posts
    assert call["url"] == "https://api.telegram.org/bot123:abc/sendMessage"
    assert call["json"]["chat_id"] == "42"
    text = call["json"]["text"]
    assert "*acme/widget*" in text
    assert "*Widget 1.2*" in text
    assert "\\*bold\\*" in text and "\\_italic\\_" in text and "\\`code\\`" in text
    assert text.endswith("...")


def test_telegram_skips_when_not_configured(posts, set_config):
    set_config(notifications={"telegram": {"enabled": True, "bot_token": "123:abc"}})
    assert asyncio.run(telegram.send_telegram_notification(RELEASE)) is False
    assert posts == []


def test_discord_embed_contents(posts, set_config):
    set_config(notifications={"discord": {"enabled": True, "webhook_url": "https://discord.example/hook"}})
    body = "y" * 1500

    assert asyncio.run(discord.send_discord_notification(RELEASE | {"body": body}))

    (call,) = posts
    assert call["url"] == "https://discord.example/hook"
    (embed,) = call["json"]["embeds"]
    assert embed["url"] == RELEASE["html_url"]
    assert "Widget 1.2" in embed["title"]
    assert embed["description"] == "y" * 1000 + "..."
    fields = {f["value"] for f in embed["fields"]}
    assert "v1.2.0" in fields
    assert "[acme/widget](https://github.com/acme/widget)" in fields


def test_discord_skips_when_disabled(posts, set_config):
    set_config(notifications={"discord": {"enabled": False, "webhook_url": "https://discord.example/hook"}})
    assert asyncio.run(discord.send_discord_notification(RELEASE)) is False
    assert posts == []
