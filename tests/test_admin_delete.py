from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.config import RepoConfig, Settings
from f_server.db import Base, get_session
from f_server.main import create_app
from f_server.models import App, Asset, Version
from f_server.storage.local import LocalStorage


def test_admin_can_delete_project_storage_and_index(tmp_path, monkeypatch) -> None:
    app, testing_session, storage = _test_app(tmp_path, monkeypatch)
    package_name = "com.example.delete"
    _create_app(testing_session, storage, package_name)

    with TestClient(app) as client:
        response = client.post(
            f"/admin/apps/{package_name}/delete",
            data={"confirm_package_name": package_name},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    assert not storage.exists("repo/com.example.delete_1_aaaaaaaa.apk")
    assert not storage.exists("repo/com.example.delete/en-US/icon.png")
    assert storage.exists("repo/index-v2.json")
    with storage.open_stream("repo/index-v2.json") as fp:
        index = json.load(fp)
    assert package_name not in index["packages"]
    with testing_session() as session:
        assert session.get(App, package_name) is None


def test_admin_project_delete_requires_package_name_confirmation(tmp_path, monkeypatch) -> None:
    app, testing_session, storage = _test_app(tmp_path, monkeypatch)
    package_name = "com.example.confirm"
    _create_app(testing_session, storage, package_name)

    with TestClient(app) as client:
        response = client.post(
            f"/admin/apps/{package_name}/delete",
            data={"confirm_package_name": "wrong.package"},
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert storage.exists("repo/com.example.confirm_1_aaaaaaaa.apk")
    with testing_session() as session:
        assert session.get(App, package_name) is not None


def test_admin_can_delete_version_storage_and_rebuild_index(tmp_path, monkeypatch) -> None:
    app, testing_session, storage = _test_app(tmp_path, monkeypatch)
    package_name = "com.example.version"
    version_id = _create_app(testing_session, storage, package_name)

    with TestClient(app) as client:
        response = client.post(f"/admin/versions/{version_id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/admin/apps/{package_name}"
    assert not storage.exists("repo/com.example.version_1_aaaaaaaa.apk")
    assert storage.exists("repo/index-v2.json")
    with storage.open_stream("repo/index-v2.json") as fp:
        index = json.load(fp)
    assert index["packages"][package_name]["versions"] == {}
    with testing_session() as session:
        assert session.get(App, package_name) is not None
        assert session.get(Version, version_id) is None


def test_admin_delete_controls_are_dangerous_and_confirmed(tmp_path, monkeypatch) -> None:
    app, testing_session, storage = _test_app(tmp_path, monkeypatch)
    package_name = "com.example.controls"
    _create_app(testing_session, storage, package_name)

    with TestClient(app) as client:
        response = client.get(f"/admin/apps/{package_name}")

    assert response.status_code == 200
    assert 'action="/admin/apps/com.example.controls/delete"' in response.text
    assert 'class="danger" type="submit">Delete project</button>' in response.text
    assert "Delete this entire project and all versions?" in response.text
    assert "prompt(" in response.text
    assert "to confirm deletion:" in response.text
    assert 'name="confirm_package_name"' in response.text
    assert "Delete this version from the repository?" in response.text


def _test_app(tmp_path, monkeypatch):
    for key in [
        "FS_REPO__KEYSTORE_PATH",
        "FS_REPO__KEYSTORE_PASS",
        "FS_REPO__KEY_ALIAS",
        "FS_REPO__KEY_PASS",
    ]:
        monkeypatch.delenv(key, raising=False)
    settings = Settings(database_url="sqlite:///:memory:", repo=RepoConfig())
    storage = LocalStorage(tmp_path / "storage")
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

    monkeypatch.setattr("f_server.routers.admin.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.services.rebuild.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.services.rebuild.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.main.create_all", lambda: None)

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return app, testing_session, storage


def _create_app(testing_session, storage: LocalStorage, package_name: str) -> int:
    apk_name = f"{package_name}_1_aaaaaaaa.apk"
    apk_key = f"repo/{apk_name}"
    icon_key = f"repo/{package_name}/en-US/icon.png"
    storage.put(apk_key, BytesIO(b"apk"), "application/vnd.android.package-archive")
    storage.put(icon_key, BytesIO(b"png"), "image/png")
    with testing_session() as session:
        app = App(package_name=package_name, name="Delete Me", summary="", categories=[])
        session.add(app)
        session.flush()
        version = Version(
            package_name=package_name,
            version_name="1.0",
            version_code=1,
            apk_name=apk_name,
            storage_key=apk_key,
            size=3,
            sha256_hash="b" * 64,
            min_sdk=23,
            target_sdk=35,
            max_sdk=None,
            nativecode=[],
            permissions=[],
            signer_fingerprint="a" * 64,
            release_channel="release",
        )
        session.add(version)
        session.add(Asset(package_name=package_name, locale="en-US", kind="icon", storage_key=icon_key))
        session.commit()
        return version.id
