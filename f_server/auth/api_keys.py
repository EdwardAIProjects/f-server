from __future__ import annotations

import fnmatch
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from f_server.db import get_session
from f_server.models import ApiKey, AuditLog, utcnow

_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CreatedApiKey:
    model: ApiKey
    secret: str


def generate_secret() -> str:
    return "fsk_" + secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    return _hasher.hash(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, secret)
    except VerifyMismatchError:
        return False


def create_api_key(
    session: Session,
    label: str,
    scopes: list[str],
    permissions: list[str] | None = None,
    created_by: str | None = None,
) -> CreatedApiKey:
    secret = generate_secret()
    model = ApiKey(
        label=label,
        hashed_secret=hash_secret(secret),
        allowed_package_globs=scopes,
        permissions=permissions or ["upload", "create"],
        created_by=created_by,
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return CreatedApiKey(model=model, secret=secret)


def authenticate_secret(session: Session, secret: str) -> ApiKey | None:
    for api_key in session.scalars(select(ApiKey).where(ApiKey.revoked.is_(False))):
        if verify_secret(secret, api_key.hashed_secret):
            api_key.last_used_at = utcnow()
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            return api_key
    return None


def package_allowed(api_key: ApiKey, package_name: str) -> bool:
    return any(fnmatch.fnmatchcase(package_name, pattern) for pattern in api_key.allowed_package_globs)


def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> ApiKey:
    if not credentials or credentials.scheme.lower() != "bearer":
        _audit(session, request, None, "auth", None, None, "401")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    api_key = authenticate_secret(session, credentials.credentials)
    if api_key is None:
        _audit(session, request, None, "auth", None, None, "401")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")
    return api_key


def _audit(
    session: Session,
    request: Request | None,
    actor: str | None,
    action: str,
    package_name: str | None,
    version_code: int | None,
    result: str,
) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            package_name=package_name,
            version_code=version_code,
            ip=request.client.host if request and request.client else None,
            result=result,
        )
    )
    session.commit()


def audit_event(
    session: Session,
    request: Request | None,
    actor: str | None,
    action: str,
    package_name: str | None,
    version_code: int | None,
    result: str,
) -> None:
    _audit(session, request, actor, action, package_name, version_code, result)
