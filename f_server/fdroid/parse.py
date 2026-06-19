from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fdroidserver import common


@dataclass(frozen=True)
class ApkInfo:
    package_name: str
    version_code: int
    version_name: str | None
    signer_fingerprint: str
    min_sdk: int | None = None
    target_sdk: int | None = None
    max_sdk: int | None = None
    permissions: tuple[str, ...] = ()
    nativecode: tuple[str, ...] = ()
    label: str | None = None


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_apk(path: str | Path) -> ApkInfo:
    apk_path = str(path)
    package_name, version_code, version_name = common.get_apk_id(apk_path)
    cert = common.get_first_signer_certificate(apk_path)
    if not cert:
        raise ValueError("APK has no readable signing certificate")
    signer = common.signer_fingerprint(cert)

    apk = common.get_androguard_APK(apk_path)
    min_sdk = _safe_int(getattr(apk, "get_min_sdk_version", lambda: None)())
    target_sdk = _safe_int(getattr(apk, "get_target_sdk_version", lambda: None)())
    max_sdk = _safe_int(getattr(apk, "get_max_sdk_version", lambda: None)())
    permissions = tuple(sorted(getattr(apk, "get_permissions", lambda: [])() or []))
    nativecode = tuple(sorted(getattr(apk, "get_libraries", lambda: [])() or []))
    label = getattr(apk, "get_app_name", lambda: None)()

    return ApkInfo(
        package_name=package_name,
        version_code=int(version_code),
        version_name=version_name or None,
        signer_fingerprint=signer,
        min_sdk=min_sdk,
        target_sdk=target_sdk,
        max_sdk=max_sdk,
        permissions=permissions,
        nativecode=nativecode,
        label=label,
    )
