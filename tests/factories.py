"""Test data builders."""


def make_release(tag, body="", name=None):
    """A minimal payload shaped like the GitHub releases API response."""
    return {
        "tag_name": tag,
        "name": name if name is not None else tag,
        "body": body,
        "html_url": f"https://github.com/acme/widget/releases/tag/{tag}",
        "published_at": "2026-01-01T00:00:00Z",
    }
