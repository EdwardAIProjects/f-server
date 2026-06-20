from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from f_server.routers.repo import get_repo_file


class UrlStorage:
    def __init__(self) -> None:
        self.objects = {
            "repo/entry.jar": b"jar",
            "repo/index-v1.jar": b"jar",
            "repo/index-v2.json": b"{}",
            "repo/app.apk": b"apk",
        }
        self.urls_requested: list[str] = []

    def url_for(self, key: str, expires: int = 300) -> str | None:
        self.urls_requested.append(key)
        return f"https://objects.example.com/{key}"

    def exists(self, key: str) -> bool:
        return key in self.objects

    def open_stream(self, key: str):
        return BytesIO(self.objects[key])


@pytest.mark.parametrize("path", ["entry.jar", "index-v1.jar", "index-v2.json", "app.apk"])
def test_repo_files_are_served_without_redirect(path, monkeypatch) -> None:
    storage = UrlStorage()
    monkeypatch.setattr("f_server.routers.repo.get_storage", lambda: storage)

    response = get_repo_file(path)

    assert isinstance(response, StreamingResponse)
    assert storage.urls_requested == []


def test_missing_fdroid_index_file_returns_404(monkeypatch) -> None:
    storage = UrlStorage()
    monkeypatch.setattr("f_server.routers.repo.get_storage", lambda: storage)

    with pytest.raises(HTTPException) as exc_info:
        get_repo_file("index-v1.json")

    assert exc_info.value.status_code == 404
    assert storage.urls_requested == []
