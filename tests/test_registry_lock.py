from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.config import DownloadAuthConfig, Settings
from f_server.db import Base, get_session
from f_server.main import create_app
from f_server.models import AuditLog
from f_server.storage.local import LocalStorage


def test_admin_can_lock_and_unlock_registry_downloads(tmp_path, monkeypatch) -> None:
    app, testing_session = _test_app(
        tmp_path,
        monkeypatch,
        Settings(database_url="sqlite:///:memory:", download_auth=DownloadAuthConfig(password="secret")),
    )

    with TestClient(app) as client:
        public = client.get("/repo/index-v2.json")
        assert public.status_code == 200

        locked = client.post("/admin/registry/lock", follow_redirects=False)
        assert locked.status_code == 303

        without_password = client.get("/repo/index-v2.json")
        assert without_password.status_code == 401

        wrong_password = client.get("/repo/index-v2.json", auth=("fdroid", "wrong"))
        assert wrong_password.status_code == 401

        with_password = client.get("/repo/index-v2.json", auth=("fdroid", "secret"))
        assert with_password.status_code == 200

        unlocked = client.post("/admin/registry/unlock", follow_redirects=False)
        assert unlocked.status_code == 303

        public_again = client.get("/repo/index-v2.json")
        assert public_again.status_code == 200

    with testing_session() as session:
        actions = [row.action for row in session.scalars(select(AuditLog).order_by(AuditLog.id))]
        assert actions == ["registry.lock", "registry.unlock"]


def test_admin_cannot_lock_registry_without_download_password(tmp_path, monkeypatch) -> None:
    app, _testing_session = _test_app(tmp_path, monkeypatch, Settings(database_url="sqlite:///:memory:"))

    with TestClient(app) as client:
        response = client.post("/admin/registry/lock")

    assert response.status_code == 400
    assert "Download password is not configured." in response.text


def _test_app(tmp_path, monkeypatch, settings: Settings):
    storage = LocalStorage(tmp_path / "storage")
    repo_file = storage.local_path("repo/index-v2.json")
    repo_file.parent.mkdir(parents=True, exist_ok=True)
    repo_file.write_text("{}")

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

    monkeypatch.setattr("f_server.auth.admin.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.routers.admin.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.routers.repo.get_storage", lambda: storage)
    monkeypatch.setattr("f_server.main.create_all", lambda: None)

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return app, testing_session
