from __future__ import annotations

import secrets

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from f_server.auth.api_keys import verify_secret
from f_server.config import get_settings
from f_server.db import get_session
from f_server.models import RegistrySettings

_basic = HTTPBasic(auto_error=False)
_oauth = OAuth()
_oauth_registered = False


def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(_basic),
) -> str:
    cfg = get_settings().admin_auth
    if cfg.mode == "none":
        return "admin"
    if cfg.mode == "basic":
        if not cfg.password:
            raise HTTPException(status_code=500, detail="admin basic auth password is not configured")
        ok = credentials and secrets.compare_digest(credentials.username, cfg.username)
        ok = bool(ok and secrets.compare_digest(credentials.password, cfg.password))
        if ok:
            return credentials.username
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    user = request.session.get("admin_user")
    if user:
        return str(user)
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="OIDC login required",
        headers={"Location": "/admin/login"},
    )


def require_download_auth(
    credentials: HTTPBasicCredentials | None = Depends(_basic),
    session: Session = Depends(get_session),
) -> None:
    registry_settings = session.get(RegistrySettings, 1)
    if not registry_settings or not registry_settings.downloads_locked:
        return
    if not registry_settings.username or not registry_settings.hashed_password:
        raise HTTPException(status_code=500, detail="registry password is not configured")
    ok = credentials and secrets.compare_digest(credentials.username, registry_settings.username)
    ok = bool(ok and verify_secret(credentials.password, registry_settings.hashed_password))
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid download credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def oidc_enabled() -> bool:
    return get_settings().admin_auth.mode == "oidc"


def oidc_client():
    global _oauth_registered
    cfg = get_settings().admin_auth
    if not oidc_enabled():
        raise HTTPException(status_code=404, detail="OIDC is not enabled")
    if not (cfg.issuer and cfg.client_id and cfg.client_secret):
        raise HTTPException(status_code=500, detail="OIDC issuer/client credentials are not configured")
    if not _oauth_registered:
        _oauth.register(
            name="admin_oidc",
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            server_metadata_url=f"{cfg.issuer.rstrip('/')}/.well-known/openid-configuration",
            client_kwargs={"scope": cfg.scopes},
        )
        _oauth_registered = True
    return _oauth.admin_oidc
