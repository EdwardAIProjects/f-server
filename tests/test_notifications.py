from __future__ import annotations

from datetime import datetime, timezone

import httpx

from f_server.config import NotificationsConfig, RepoConfig
from f_server.models import App, Version
from f_server.services.notifications import _discord_payload, notify_app_published


def test_discord_publish_notification_is_skipped_without_webhook(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("f_server.services.notifications.httpx.post", lambda *args, **kwargs: calls.append(args))

    notify_app_published(
        _app(),
        _version(),
        RepoConfig(url="https://example.test/repo"),
        NotificationsConfig(),
    )

    assert calls == []


def test_discord_publish_notification_posts_payload(monkeypatch) -> None:
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json, timeout))
        return httpx.Response(204, request=httpx.Request("POST", url))

    monkeypatch.setattr("f_server.services.notifications.httpx.post", fake_post)

    notify_app_published(
        _app(),
        _version(),
        RepoConfig(url="https://example.test/repo"),
        NotificationsConfig(
            discord_webhook_url="https://discord.test/webhook",
            discord_username="publisher",
            discord_timeout_seconds=2.5,
        ),
    )

    assert calls == [
        (
            "https://discord.test/webhook",
            _discord_payload(
                _app(),
                _version(),
                RepoConfig(url="https://example.test/repo"),
                NotificationsConfig(
                    discord_webhook_url="https://discord.test/webhook",
                    discord_username="publisher",
                    discord_timeout_seconds=2.5,
                ),
            ),
            2.5,
        )
    ]
    assert calls[0][1]["allowed_mentions"] == {"parse": []}
    assert "content" not in calls[0][1]


def test_discord_publish_notification_uses_rich_embed_shape() -> None:
    payload = _discord_payload(
        _app(),
        _version(),
        RepoConfig(
            name="Example Repo",
            url="https://example.test/repo",
            icon="https://example.test/icon.png",
        ),
        NotificationsConfig(discord_username="publisher"),
    )

    embed = payload["embeds"][0]
    assert embed["author"] == {"name": "Example Repo"}
    assert embed["title"] == "Example 1.2.3 is live"
    assert embed["url"] == "https://example.test/repo"
    assert embed["color"] == 0x2ECC71
    assert embed["thumbnail"] == {"url": "https://example.test/icon.png"}
    assert embed["footer"] == {"text": "f-server publish notification"}
    assert embed["timestamp"] == "2026-06-19T12:00:00+00:00"
    assert {"name": "Size", "value": "120.6 KiB", "inline": True} in embed["fields"]
    assert {"name": "SHA-256", "value": "`aaaaaaaaaaaa...aaaaaaaa`", "inline": False} in embed["fields"]


def test_discord_publish_notification_failure_is_logged(monkeypatch, caplog) -> None:
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("discord unavailable")

    monkeypatch.setattr("f_server.services.notifications.httpx.post", fake_post)

    notify_app_published(
        _app(),
        _version(),
        RepoConfig(),
        NotificationsConfig(discord_webhook_url="https://discord.test/webhook"),
    )

    assert "failed to send Discord publish notification" in caplog.text


def test_invalid_discord_webhook_url_is_logged(monkeypatch, caplog) -> None:
    def fake_post(url, json, timeout):
        raise httpx.InvalidURL("invalid URL")

    monkeypatch.setattr("f_server.services.notifications.httpx.post", fake_post)

    notify_app_published(
        _app(),
        _version(),
        RepoConfig(),
        NotificationsConfig(discord_webhook_url="not-a-url"),
    )

    assert "failed to send Discord publish notification" in caplog.text


def _app() -> App:
    return App(
        package_name="com.example.app",
        name="Example",
        summary="Example summary",
        categories=["Tools"],
    )


def _version() -> Version:
    return Version(
        package_name="com.example.app",
        version_name="1.2.3",
        version_code=123,
        apk_name="com.example.app_123_aaaaaaa.apk",
        storage_key="repo/com.example.app_123_aaaaaaa.apk",
        size=123456,
        sha256_hash="a" * 64,
        min_sdk=23,
        target_sdk=35,
        max_sdk=None,
        nativecode=["arm64-v8a"],
        permissions=[],
        signer_fingerprint="b" * 64,
        release_channel="release",
        added_at=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
    )
