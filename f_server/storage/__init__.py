from __future__ import annotations

from functools import lru_cache

from f_server.config import get_settings
from f_server.storage.base import StorageBackend
from f_server.storage.local import LocalStorage
from f_server.storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    cfg = settings.storage
    if cfg.backend == "s3":
        return S3Storage(
            bucket=cfg.bucket,
            region=cfg.region,
            endpoint=cfg.endpoint,
            public_endpoint=cfg.public_base_url,
            access_key=cfg.access_key,
            secret_key=cfg.secret_key,
        )
    return LocalStorage(cfg.local_path, cfg.public_base_url)
