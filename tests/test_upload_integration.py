from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.auth.api_keys import create_api_key
from f_server.config import RepoConfig, Settings, StorageConfig
from f_server.db import Base, get_session
from f_server.main import create_app
from f_server.models import AllowedSigningKey, App, AuditLog, Version
from f_server.storage.local import LocalStorage
from tests.apk_factory import android_tools_available, build_signed_apk


pytestmark = pytest.mark.skipif(not android_tools_available(), reason="Android SDK/JBR tools are unavailable")


def test_real_apk_upload_tofu_idempotency_scope_and_cert_mismatch(tmp_path, monkeypatch) -> None:
    storage = LocalStorage(tmp_path / "storage")
    settings = Settings(
        database_url="sqlite:///:memory:",
        repo=RepoConfig(),
        storage=StorageConfig(),
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

    monkeypatch.setattr("f_server.routers.upload.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.routers.repo.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.services.rebuild.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.services.rebuild.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.main.create_all", lambda: None)

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    package_name = "com.example.fixture"
    apk_v1 = build_signed_apk(tmp_path / "apks", package_name, 1, "1.0", "signer-one")
    apk_v2_wrong_signer = build_signed_apk(tmp_path / "apks", package_name, 2, "2.0", "signer-two")

    with testing_session() as session:
        upload_key = create_api_key(session, "fixture", [package_name]).secret
        wrong_scope_key = create_api_key(session, "wrong", ["org.other.*"]).secret

    with TestClient(app) as client:
        missing_key = _upload(client, apk_v1, None)
        assert missing_key.status_code == 401

        wrong_scope = _upload(client, apk_v1, wrong_scope_key)
        assert wrong_scope.status_code == 403
        assert wrong_scope.json()["detail"] == "package is outside API key scope"

        created = _upload(
            client,
            apk_v1,
            upload_key,
            {"summary": "Fixture summary", "categories": ["Tools"]},
            screenshots=[("screen.png", b"not-a-real-png")],
        )
        assert created.status_code == 200
        created_json = created.json()
        assert created_json["status"] == "created"
        assert created_json["packageName"] == package_name
        assert created_json["versionCode"] == 1
        assert created_json["indexFiles"] == ["repo/index-v2.json", "repo/entry.json", "repo/index-v1.json"]

        idempotent = _upload(client, apk_v1, upload_key)
        assert idempotent.status_code == 200
        assert idempotent.json()["status"] == "exists"

        mismatch = _upload(client, apk_v2_wrong_signer, upload_key)
        assert mismatch.status_code == 422
        assert "signing certificate" in mismatch.json()["detail"]

        package = client.get(f"/api/v1/packages/{package_name}")
        assert package.status_code == 200
        assert package.json()["versions"][0]["versionCode"] == 1

        index = client.get("/repo/index-v2.json")
        assert index.status_code == 200
        index_json = index.json()
        assert package_name in index_json["packages"]

    with testing_session() as session:
        assert session.get(App, package_name) is not None
        assert session.scalar(select(AllowedSigningKey).where(AllowedSigningKey.package_name == package_name))
        assert session.scalar(select(Version).where(Version.package_name == package_name)).version_code == 1
        assert storage.exists(f"repo/{package_name}/en-US/phoneScreenshots/01.png")
        assert session.scalar(select(AuditLog).where(AuditLog.result == "422-cert"))


def _upload(
    client: TestClient,
    apk_path,
    key: str | None,
    metadata: dict | None = None,
    screenshots: list[tuple[str, bytes]] | None = None,
):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    data = {}
    if metadata is not None:
        data["metadata"] = json.dumps(metadata)
    with apk_path.open("rb") as fp:
        files = [("apk", (apk_path.name, fp, "application/vnd.android.package-archive"))]
        for filename, content in screenshots or []:
            files.append(("screenshots", (filename, content, "image/png")))
        return client.post(
            "/api/v1/upload",
            headers=headers,
            data=data,
            files=files,
        )
