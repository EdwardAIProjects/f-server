from __future__ import annotations

from f_server.fdroid.parse import ApkInfo
from f_server.models import Version
from f_server.routers.upload import _apply_apk_info


def test_apply_apk_info_updates_stale_version_metadata() -> None:
    version = Version(
        package_name="com.example.app",
        version_name="1.0",
        version_code=1,
        apk_name="com.example.app_1_aaaaaaa.apk",
        storage_key="repo/com.example.app_1_aaaaaaa.apk",
        size=3,
        sha256_hash="b" * 64,
        min_sdk=23,
        target_sdk=35,
        max_sdk=None,
        nativecode=["androidx.window.extensions"],
        permissions=[],
        signer_fingerprint="a" * 64,
        release_channel="release",
    )
    info = ApkInfo(
        package_name="com.example.app",
        version_code=1,
        version_name="1.0",
        signer_fingerprint="a" * 64,
        min_sdk=23,
        target_sdk=35,
        nativecode=("arm64-v8a",),
        permissions=("android.permission.INTERNET",),
    )

    changed = _apply_apk_info(version, info)

    assert changed is True
    assert version.nativecode == ["arm64-v8a"]
    assert version.permissions == ["android.permission.INTERNET"]


def test_apply_apk_info_reports_unchanged_metadata() -> None:
    version = Version(
        package_name="com.example.app",
        version_name="1.0",
        version_code=1,
        apk_name="com.example.app_1_aaaaaaa.apk",
        storage_key="repo/com.example.app_1_aaaaaaa.apk",
        size=3,
        sha256_hash="b" * 64,
        min_sdk=23,
        target_sdk=35,
        max_sdk=None,
        nativecode=["arm64-v8a"],
        permissions=["android.permission.INTERNET"],
        signer_fingerprint="a" * 64,
        release_channel="release",
    )
    info = ApkInfo(
        package_name="com.example.app",
        version_code=1,
        version_name="1.0",
        signer_fingerprint="a" * 64,
        min_sdk=23,
        target_sdk=35,
        nativecode=("arm64-v8a",),
        permissions=("android.permission.INTERNET",),
    )

    assert _apply_apk_info(version, info) is False
