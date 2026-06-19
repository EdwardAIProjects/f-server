from __future__ import annotations

import shutil
from pathlib import Path

from fdroidserver import common, signindex

from f_server.config import Settings


class SigningConfigurationError(RuntimeError):
    """Raised when repository signing settings are present but unusable."""


def signing_configured(settings: Settings) -> bool:
    repo = settings.repo
    return bool(repo.keystore_path and repo.keystore_pass and repo.key_alias and repo.key_pass)


def sign_indexes(repodir: Path, settings: Settings) -> list[Path]:
    if not _validate_signing_config(settings):
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


def _validate_signing_config(settings: Settings) -> bool:
    repo = settings.repo
    fields = {
        "FS_REPO__KEYSTORE_PATH": repo.keystore_path,
        "FS_REPO__KEYSTORE_PASS": repo.keystore_pass,
        "FS_REPO__KEY_ALIAS": repo.key_alias,
        "FS_REPO__KEY_PASS": repo.key_pass,
    }
    if not any(fields.values()):
        return False
    missing = [name for name, value in fields.items() if not value]
    if missing:
        raise SigningConfigurationError(
            "repository signing is partially configured; missing "
            + ", ".join(missing)
            + ". Set all repository signing variables or unset them all to publish unsigned indexes."
        )
    if repo.keystore_path is not None and not repo.keystore_path.is_file():
        raise SigningConfigurationError(
            f"repository signing keystore was not found at {repo.keystore_path}. "
            "Create it with "
            f"`f-server init --keystore {repo.keystore_path} --alias {repo.key_alias} --password ...` "
            "or unset the repository signing variables to publish unsigned indexes."
        )
    return True
