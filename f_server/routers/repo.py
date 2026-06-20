from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from f_server.auth.admin import require_download_auth
from f_server.storage import get_storage
from f_server.storage.local import LocalStorage

router = APIRouter(prefix="/repo", tags=["repo"], dependencies=[Depends(require_download_auth)])


@router.get("/{path:path}")
def get_repo_file(path: str):
    if not path or path.endswith("/"):
        raise HTTPException(status_code=404, detail="not found")
    key = f"repo/{path}"
    storage = get_storage()
    return _storage_response(storage, key, path)


def _storage_response(storage, key: str, path: str):
    if isinstance(storage, LocalStorage):
        local_path = storage.local_path(key)
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(local_path, media_type=_media_type(Path(path).suffix))
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="not found")
    media_type = _media_type(Path(path).suffix)
    return StreamingResponse(storage.open_stream(key), media_type=media_type)


def _media_type(suffix: str) -> str:
    return {
        ".apk": "application/vnd.android.package-archive",
        ".json": "application/json",
        ".jar": "application/java-archive",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix.lower(), "application/octet-stream")
