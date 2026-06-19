from __future__ import annotations

import shutil
from pathlib import Path

from fdroidserver import common, signindex

from f_server.config import Settings


def signing_configured(settings: Settings) -> bool:
    repo = settings.repo
    return bool(repo.keystore_path and repo.keystore_pass and repo.key_alias and repo.key_pass)


def sign_indexes(repodir: Path, settings: Settings) -> list[Path]:
    if not signing_configured(settings):
        return []
    common.config = {
        "keystore": str(settings.repo.keystore_path),
        "keystorepass": settings.repo.keystore_pass,
        "repo_keyalias": settings.repo.key_alias,
        "keypass": settings.repo.key_pass,
        "jarsigner": shutil.which("jarsigner") or "jarsigner",
        "apksigner": shutil.which("apksigner") or "apksigner",
        "smartcardoptions": [],
    }
    signindex.config = common.config
    signindex.sign_index(str(repodir), "entry.json")
    signindex.sign_index(str(repodir), "index-v1.json")
    return [repodir / "entry.jar", repodir / "index-v1.jar"]
