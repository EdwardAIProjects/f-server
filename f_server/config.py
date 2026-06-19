from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageConfig(BaseModel):
    backend: Literal["local", "s3"] = "local"
    local_path: Path = Path("./data/storage")
    endpoint: str | None = None
    bucket: str = "f-server"
    region: str = "us-east-1"
    access_key: str | None = None
    secret_key: str | None = None
    public_base_url: str | None = None


class RepoConfig(BaseModel):
    name: str = "f-server"
    description: str = "Private F-Droid repository"
    url: str = "http://localhost:8000/repo"
    icon: str | None = None
    keystore_path: Path | None = None
    keystore_pass: str | None = None
    key_alias: str | None = None
    key_pass: str | None = None


class AdminAuthConfig(BaseModel):
    mode: Literal["none", "basic", "oidc"] = "none"
    session_secret: str = "change-me"
    username: str = "admin"
    password: str | None = None
    issuer: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    redirect_url: str | None = None
    scopes: str = "openid profile email"


class DownloadAuthConfig(BaseModel):
    mode: Literal["none", "basic"] = "none"
    username: str = "fdroid"
    password: str | None = None


class UploadsConfig(BaseModel):
    onboarding: Literal["tofu_scoped"] = "tofu_scoped"
    verify_signing_keys: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FS_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite:///./f-server.db"
    storage: StorageConfig = Field(default_factory=StorageConfig)
    repo: RepoConfig = Field(default_factory=RepoConfig)
    admin_auth: AdminAuthConfig = Field(default_factory=AdminAuthConfig)
    download_auth: DownloadAuthConfig = Field(default_factory=DownloadAuthConfig)
    uploads: UploadsConfig = Field(default_factory=UploadsConfig)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


@lru_cache
def get_settings(config_path: str | None = None) -> Settings:
    path = Path(config_path or "config.yaml")
    return Settings(**_read_yaml(path))
