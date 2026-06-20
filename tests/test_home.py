from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.responses import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from f_server.config import AdminAuthConfig, Settings
from f_server.db import Base, get_session
from f_server.main import create_app


def test_homepage_renders(monkeypatch) -> None:
    monkeypatch.setattr("f_server.main.create_all", lambda: None)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/")
        favicon = client.get("/favicon.ico")

    assert response.status_code == 200
    assert "f-server" in response.text
    assert 'href="/static/favicon.ico"' in response.text
    assert 'href="/admin"' in response.text
    assert 'href="/add-repository"' in response.text
    assert 'href="/repo/index-v2.json"' in response.text
    assert 'href="/health"' in response.text
    assert "Upload API" not in response.text
    assert "F-Droid repository server" not in response.text
    assert "f-server accepts scoped CI uploads" not in response.text
    assert favicon.status_code == 200


def test_add_repository_qr_page_renders(monkeypatch) -> None:
    monkeypatch.setattr("f_server.main.create_all", lambda: None)
    app = create_app()

    with TestClient(app) as client:
        page = client.get("/add-repository")
        qr = client.get("/add-repository.svg")

    assert page.status_code == 200
    assert "Add repository" in page.text
    assert 'src="/add-repository.svg"' in page.text
    assert "http://localhost:8000/repo" in page.text
    assert qr.status_code == 200
    assert qr.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in qr.content


def test_admin_brand_links_to_homepage(monkeypatch) -> None:
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

    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert '<a class="brand" href="/" aria-label="Home">' in response.text


def test_oidc_login_uses_configured_redirect_url(monkeypatch) -> None:
    settings = Settings(
        admin_auth=AdminAuthConfig(
            mode="oidc",
            issuer="https://issuer.example.com",
            client_id="client-id",
            client_secret="client-secret",
            redirect_url="https://f-server.example.com/admin/callback",
        )
    )

    class FakeOidcClient:
        redirect_uri: str | None = None

        async def authorize_redirect(self, request, redirect_uri, code_challenge_method):
            self.redirect_uri = redirect_uri
            return Response(status_code=204)

    fake_client = FakeOidcClient()
    monkeypatch.setattr("f_server.main.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.main.create_all", lambda: None)
    monkeypatch.setattr("f_server.routers.admin.get_settings", lambda: settings)
    monkeypatch.setattr("f_server.routers.admin.oidc_enabled", lambda: True)
    monkeypatch.setattr("f_server.routers.admin.oidc_client", lambda: fake_client)

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/admin/login")

    assert response.status_code == 204
    assert fake_client.redirect_uri == "https://f-server.example.com/admin/callback"
