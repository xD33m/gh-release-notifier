"""The release check: what gets announced, and what stays quiet."""

import asyncio

import pytest

from app import database, scheduler
from tests.factories import make_release


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def github(monkeypatch):
    """Fake GitHub API: maps "owner/name" to the list of releases it returns."""
    releases: dict[str, list[dict]] = {}

    async def fake_get_releases(owner, name, per_page=10):
        return releases.get(f"{owner}/{name}", [])[:per_page]

    monkeypatch.setattr(scheduler.github_client, "get_releases", fake_get_releases)
    return releases


@pytest.fixture
def sent(monkeypatch):
    """Capture notifications instead of calling Telegram/Discord."""
    messages: list[dict] = []

    async def fake_send(release):
        messages.append(release)

    monkeypatch.setattr(scheduler, "send_notifications", fake_send)
    return messages


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    """The check pauses between repositories; skip that in tests."""
    real_sleep = asyncio.sleep

    async def instant(_seconds, *args, **kwargs):
        await real_sleep(0)

    monkeypatch.setattr(scheduler.asyncio, "sleep", instant)


def test_initial_sync_adds_configured_repos_without_notifying(set_config, github, sent):
    set_config(repositories=["acme/widget"])
    github["acme/widget"] = [make_release("v1.0.0"), make_release("v0.9.0")]

    run(scheduler.initial_sync())

    repos = run(database.get_repositories())
    assert [(r["owner"], r["name"]) for r in repos] == [("acme", "widget")]
    assert sent == []
    assert run(database.get_unnotified_releases()) == []


def test_new_release_is_announced_exactly_once(github, sent):
    run(database.add_repository("acme", "widget"))
    github["acme/widget"] = [make_release("v1.0.0")]
    run(scheduler.check_releases())
    assert [m["tag_name"] for m in sent] == ["v1.0.0"]

    github["acme/widget"] = [make_release("v1.1.0"), make_release("v1.0.0")]
    run(scheduler.check_releases())
    run(scheduler.check_releases())

    assert [m["tag_name"] for m in sent] == ["v1.0.0", "v1.1.0"]
    assert sent[1]["owner"] == "acme" and sent[1]["repo_name"] == "widget"
    assert run(database.get_unnotified_releases()) == []


def test_muted_tag_suppresses_notifications_but_records_release(github, sent):
    tag_id = run(database.add_tag("muted"))
    run(database.update_tag(tag_id, notifications_enabled=False))
    run(database.add_repository("acme", "quiet", tag_id))
    github["acme/quiet"] = [make_release("v2.0.0")]

    run(scheduler.check_releases())

    assert sent == []
    assert [r["tag_name"] for r in run(database.get_releases())] == ["v2.0.0"]
    assert run(database.get_unnotified_releases()) == []


def test_send_notifications_uses_enabled_channels_only(monkeypatch, set_config):
    set_config(notifications={"telegram": {"enabled": False}, "discord": {"enabled": True}})
    calls = []

    async def fake_telegram(release):
        calls.append("telegram")

    async def fake_discord(release):
        calls.append("discord")

    monkeypatch.setattr(scheduler.telegram, "send_telegram_notification", fake_telegram)
    monkeypatch.setattr(scheduler.discord, "send_discord_notification", fake_discord)

    run(scheduler.send_notifications({"tag_name": "v1"}))

    assert calls == ["discord"]
