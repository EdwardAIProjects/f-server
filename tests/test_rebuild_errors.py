from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.config import RepoConfig, Settings
from f_server.db import Base, get_session
from f_server.fdroid.sign import SigningConfigurationError, sign_indexes
from f_server.main import create_app


def test_sign_indexes_reports_missing_keystore(tmp_path) -> None:
    settings = Settings(
        repo=RepoConfig(
            keystore_path=tmp_path / "missing.p12",
            keystore_pass="change-me",
            key_alias="f-server",
            key_pass="change-me",
        )
    )

    with pytest.raises(SigningConfigurationError, match="keystore was not found"):
        sign_indexes(tmp_path / "repo", settings)


def test_admin_rebuild_shows_signing_configuration_error(tmp_path, monkeypatch) -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        repo=RepoConfig(
            keystore_path=tmp_path / "missing.p12",
            keystore_pass="change-me",
            key_alias="f-server",
            key_pass="change-me",
        ),
    )
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_session():
        with testing_session() as session:
            yield session

    monkeypatch.setattr("f_server.services.rebuild.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.main.create_all", lambda: None)

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        response = client.post("/admin/rebuild")

    assert response.status_code == 400
    assert "Rebuild failed" in response.text
    assert "repository signing keystore was not found" in response.text
    assert str(tmp_path / "missing.p12") in response.text
