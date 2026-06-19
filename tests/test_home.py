from __future__ import annotations

from fastapi.testclient import TestClient

from f_server.main import create_app


def test_homepage_renders(monkeypatch) -> None:
    monkeypatch.setattr("f_server.main.create_all", lambda: None)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "f-server" in response.text
    assert 'href="/admin"' in response.text
    assert 'href="/repo/index-v2.json"' in response.text
    assert 'href="/health"' in response.text
    assert "Upload API" not in response.text
    assert "F-Droid repository server" not in response.text
    assert "f-server accepts scoped CI uploads" not in response.text
