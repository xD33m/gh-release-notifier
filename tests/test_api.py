"""HTTP endpoints, without starting the scheduler or calling GitHub.

The TestClient is used without a ``with`` block, so the app's lifespan (initial
sync + scheduler) does not run; the database is set up by the conftest fixture.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import database, main
from tests.factories import make_release


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_dashboard_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "GitHub Release Notifier" in response.text


def test_add_repo_rejects_invalid_format(client):
    response = client.post("/repos/add", data={"repo": "not-a-repo"})
    assert response.status_code == 400


def test_add_repo_rejects_unknown_repo(client, monkeypatch):
    async def not_found(owner, name):
        return False

    monkeypatch.setattr(main.github_client, "validate_repository", not_found)
    response = client.post("/repos/add", data={"repo": "acme/missing"})
    assert response.status_code == 404


def test_add_repo_stores_existing_releases_as_already_notified(client, monkeypatch):
    async def exists(owner, name):
        return True

    async def releases(owner, name, per_page=10):
        return [make_release("v1.0.0")]

    monkeypatch.setattr(main.github_client, "validate_repository", exists)
    monkeypatch.setattr(main.github_client, "get_releases", releases)

    response = client.post("/repos/add", data={"repo": " acme/widget "}, follow_redirects=False)
    assert response.status_code == 303

    repos = client.get("/api/repos").json()
    assert [(r["owner"], r["name"]) for r in repos] == [("acme", "widget")]
    assert [r["tag_name"] for r in client.get("/api/releases").json()] == ["v1.0.0"]
    assert asyncio.run(database.get_unnotified_releases()) == []

    duplicate = client.post("/repos/add", data={"repo": "acme/widget"})
    assert duplicate.status_code == 400


def test_remove_repo(client):
    asyncio.run(database.add_repository("acme", "widget"))
    response = client.post("/repos/remove", data={"repo": "acme/widget"}, follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/api/repos").json() == []


def test_tags_api(client):
    response = client.post("/tags/add", data={"name": "tools", "color": "#123456"}, follow_redirects=False)
    assert response.status_code == 303
    (tag,) = client.get("/api/tags").json()
    assert tag["name"] == "tools" and tag["repo_count"] == 0

    toggled = client.post(f"/tags/{tag['id']}/toggle-notifications").json()
    assert toggled == {"status": "success", "notifications_enabled": False}


def test_debug_config_does_not_leak_telegram_credentials(client, set_config):
    set_config(notifications={"telegram": {"enabled": True, "bot_token": "123456789:SECRET", "chat_id": "424242"}})

    response = client.get("/api/debug-config")

    assert response.status_code == 200
    assert response.json()["telegram"] == {"enabled": True, "bot_token_set": True, "chat_id_set": True}
    assert "123456" not in response.text and "424242" not in response.text
