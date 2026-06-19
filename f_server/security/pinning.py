from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from f_server.models import AllowedSigningKey, App


def signer_allowed(session: Session, package_name: str, fingerprint: str) -> bool:
    return (
        session.scalar(
            select(AllowedSigningKey).where(
                AllowedSigningKey.package_name == package_name,
                AllowedSigningKey.sha256_fingerprint == fingerprint,
            )
        )
        is not None
    )


def pin_first_signer(session: Session, app: App, fingerprint: str, added_by: str | None) -> AllowedSigningKey:
    signing_key = AllowedSigningKey(
        package_name=app.package_name,
        sha256_fingerprint=fingerprint,
        added_by=added_by,
    )
    session.add(signing_key)
    return signing_key
