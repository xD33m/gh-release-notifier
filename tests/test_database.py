import asyncio

from app import database
from tests.factories import make_release


def run(coro):
    return asyncio.run(coro)


def test_repository_can_only_be_added_once():
    first = run(database.add_repository("acme", "widget"))
    second = run(database.add_repository("acme", "widget"))

    assert isinstance(first, int)
    assert second is None
    assert [(r["owner"], r["name"]) for r in run(database.get_repositories())] == [("acme", "widget")]


def test_release_is_new_only_the_first_time():
    repo_id = run(database.add_repository("acme", "widget"))

    release_id, is_new = run(database.add_release(repo_id, make_release("v1.0.0")))
    again_id, again_new = run(database.add_release(repo_id, make_release("v1.0.0")))

    assert is_new and isinstance(release_id, int)
    assert (again_id, again_new) == (None, False)


def test_unnotified_releases_until_marked():
    repo_id = run(database.add_repository("acme", "widget"))
    release_id, _ = run(database.add_release(repo_id, make_release("v1.0.0")))

    assert [r["tag_name"] for r in run(database.get_unnotified_releases())] == ["v1.0.0"]

    run(database.mark_release_notified(release_id))
    assert run(database.get_unnotified_releases()) == []


def test_tag_filter_and_notification_toggle():
    tag_id = run(database.add_tag("emulators"))
    run(database.add_repository("acme", "tagged", tag_id))
    run(database.add_repository("acme", "untagged"))

    tagged_only = run(database.get_repositories(tag_id=tag_id))
    assert [r["name"] for r in tagged_only] == ["tagged"]

    run(database.update_tag(tag_id, notifications_enabled=False))
    notifying = run(database.get_repositories_with_notifications())
    assert [r["name"] for r in notifying] == ["untagged"]


def test_duplicate_tag_names_are_rejected():
    assert isinstance(run(database.add_tag("tools")), int)
    assert run(database.add_tag("tools")) is None


def test_releases_are_newest_first():
    repo_id = run(database.add_repository("acme", "widget"))
    old = make_release("v1.0.0") | {"published_at": "2026-01-01T00:00:00Z"}
    new = make_release("v2.0.0") | {"published_at": "2026-02-01T00:00:00Z"}
    run(database.add_release(repo_id, old))
    run(database.add_release(repo_id, new))

    releases = run(database.get_releases())
    assert [r["tag_name"] for r in releases] == ["v2.0.0", "v1.0.0"]
    assert releases[0]["owner"] == "acme" and releases[0]["repo_name"] == "widget"
