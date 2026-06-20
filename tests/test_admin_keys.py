from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.auth.api_keys import create_api_key
from f_server.db import Base, get_session
from f_server.main import create_app
from f_server.models import ApiKey


def test_api_keys_have_dedicated_admin_page(monkeypatch) -> None:
    app, _testing_session = _test_app(monkeypatch)

    with TestClient(app) as client:
        dashboard = client.get("/admin")
        keys = client.get("/admin/keys")

    assert dashboard.status_code == 200
    assert 'href="/admin/keys"' in dashboard.text
    assert "<h1>API Keys</h1>" not in dashboard.text
    assert keys.status_code == 200
    assert "<h1>API Keys</h1>" in keys.text
    assert 'action="/admin/keys"' in keys.text


def test_admin_can_create_key_from_keys_page(monkeypatch) -> None:
    app, testing_session = _test_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/admin/keys",
            data={"label": "ci", "scope": "com.example.app, org.example.*"},
        )

    assert response.status_code == 200
    assert "<h1>API Keys</h1>" in response.text
    assert "New key secret" in response.text
    assert "fsk_" in response.text
    assert "com.example.app, org.example.*" in response.text
    with testing_session() as session:
        key = session.scalar(select(ApiKey).where(ApiKey.label == "ci"))
        assert key is not None
        assert key.allowed_package_globs == ["com.example.app", "org.example.*"]


def test_admin_revoke_key_returns_to_keys_page(monkeypatch) -> None:
    app, testing_session = _test_app(monkeypatch)
    with testing_session() as session:
        key_id = create_api_key(session, "ci", ["com.example.app"]).model.id

    with TestClient(app) as client:
        response = client.post(f"/admin/keys/{key_id}/revoke", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/keys"
    with testing_session() as session:
        assert session.get(ApiKey, key_id).revoked is True


def _test_app(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_session():
        with testing_session() as session:
            yield session

    monkeypatch.setattr("f_server.main.create_all", lambda: None)
    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return app, testing_session
