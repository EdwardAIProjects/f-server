from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from f_server.config import NotificationsConfig, RepoConfig
from f_server.models import App, Version

logger = logging.getLogger(__name__)
DISCORD_EMBED_GREEN = 0x2ECC71


def notify_app_published(app: App, version: Version, repo: RepoConfig, config: NotificationsConfig) -> None:
    webhook_url = config.discord_webhook_url
    if not webhook_url:
        return

    payload = _discord_payload(app, version, repo, config)
    try:
        response = httpx.post(webhook_url, json=payload, timeout=config.discord_timeout_seconds)
        response.raise_for_status()
    except (httpx.HTTPError, httpx.InvalidURL):
        logger.warning("failed to send Discord publish notification", exc_info=True)


def _discord_payload(
    app: App,
    version: Version,
    repo: RepoConfig,
    config: NotificationsConfig,
) -> dict:
    app_name = app.name or app.package_name
    version_label = version.version_name or f"code {version.version_code}"
    sdk = _sdk_range(version)
    fields = [
        {"name": "Package", "value": f"`{app.package_name}`", "inline": False},
        {"name": "Version", "value": f"`{version_label}`", "inline": True},
        {"name": "Version code", "value": str(version.version_code), "inline": True},
        {"name": "Channel", "value": version.release_channel.title(), "inline": True},
        {"name": "APK", "value": f"`{version.apk_name}`", "inline": False},
        {"name": "Size", "value": _format_size(version.size), "inline": True},
        {"name": "SDK", "value": sdk, "inline": True},
        {"name": "Native code", "value": _native_code(version), "inline": True},
        {"name": "SHA-256", "value": f"`{_short_hash(version.sha256_hash)}`", "inline": False},
    ]
    if repo.url:
        fields.append({"name": "Repository", "value": f"[Open repository]({repo.url})", "inline": False})

    embed = {
        "author": {"name": repo.name},
        "title": f"{app_name} {version_label} is live",
        "color": DISCORD_EMBED_GREEN,
        "fields": fields,
        "footer": {"text": "f-server publish notification"},
        "timestamp": _timestamp(version),
    }
    if repo.url:
        embed["url"] = repo.url
    if app.summary:
        embed["description"] = app.summary
    if repo.icon and repo.icon.startswith(("http://", "https://")):
        embed["thumbnail"] = {"url": repo.icon}

    return {
        "username": config.discord_username,
        "allowed_mentions": {"parse": []},
        "embeds": [embed],
    }


def _format_size(size: int) -> str:
    units = ("bytes", "KiB", "MiB", "GiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{size:,} bytes"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size:,} bytes"


def _sdk_range(version: Version) -> str:
    minimum = str(version.min_sdk) if version.min_sdk is not None else "any"
    target = str(version.target_sdk) if version.target_sdk is not None else "unknown"
    if version.max_sdk is None:
        return f"min {minimum} / target {target}"
    return f"min {minimum} / target {target} / max {version.max_sdk}"


def _native_code(version: Version) -> str:
    if not version.nativecode:
        return "universal"
    return ", ".join(f"`{abi}`" for abi in version.nativecode[:3])


def _short_hash(value: str) -> str:
    if len(value) <= 16:
        return value
    return f"{value[:12]}...{value[-8:]}"


def _timestamp(version: Version) -> str:
    added_at = version.added_at or datetime.now(timezone.utc)
    return added_at.astimezone(timezone.utc).isoformat()
