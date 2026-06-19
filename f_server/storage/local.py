from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from f_server.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, root: Path, public_base_url: str | None = None) -> None:
        self.root = root
        self.public_base_url = public_base_url
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if key.startswith("/") or ".." in Path(key).parts:
            raise ValueError("invalid storage key")
        return self.root / key

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as out:
            while chunk := fileobj.read(1024 * 1024):
                out.write(chunk)

    def open_stream(self, key: str) -> BinaryIO:
        return self._path(key).open("rb")

    def url_for(self, key: str, expires: int = 300) -> str | None:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{quote(key)}"
        return None

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def local_path(self, key: str) -> Path:
        return self._path(key)
