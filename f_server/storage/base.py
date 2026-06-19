from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def open_stream(self, key: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    def url_for(self, key: str, expires: int = 300) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError
