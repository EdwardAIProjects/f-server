from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from f_server.auth.admin import oidc_client, oidc_enabled, require_admin
from f_server.auth.api_keys import create_api_key
from f_server.db import get_session
from f_server.models import AllowedSigningKey, ApiKey, App, AuditLog, Version
from f_server.services.rebuild import rebuild_repo

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="f_server/templates")


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    apps = session.scalars(
        select(App).options(selectinload(App.versions), selectinload(App.signing_keys)).order_by(App.package_name)
    ).all()
    keys = session.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    return templates.TemplateResponse(request, "admin/index.html", {"apps": apps, "keys": keys})


@router.get("/apps/{package_name}", response_class=HTMLResponse)
def app_detail(
    package_name: str,
    request: Request,
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    app = session.scalar(
        select(App)
        .where(App.package_name == package_name)
        .options(selectinload(App.versions), selectinload(App.signing_keys), selectinload(App.assets))
    )
    if app is None:
        raise HTTPException(status_code=404, detail="app not found")
    return templates.TemplateResponse(request, "admin/app.html", {"app": app})


@router.post("/apps/{package_name}/metadata")
def update_app_metadata(
    package_name: str,
    name: str = Form(""),
    summary: str = Form(""),
    description: str = Form(""),
    categories: str = Form(""),
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    app = session.get(App, package_name)
    if app is None:
        raise HTTPException(status_code=404, detail="app not found")
    app.name = name or None
    app.summary = summary or None
    app.description = description or None
    app.categories = [item.strip() for item in categories.split(",") if item.strip()]
    session.commit()
    return RedirectResponse(f"/admin/apps/{package_name}", status_code=303)


@router.post("/apps/{package_name}/signing-keys")
def add_signing_key(
    package_name: str,
    fingerprint: str = Form(...),
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    app = session.get(App, package_name)
    if app is None:
        raise HTTPException(status_code=404, detail="app not found")
    session.add(
        AllowedSigningKey(
            package_name=package_name,
            sha256_fingerprint=fingerprint.lower().replace(":", ""),
            added_by=admin,
        )
    )
    session.commit()
    return RedirectResponse(f"/admin/apps/{package_name}", status_code=303)


@router.post("/versions/{version_id}/delete")
def delete_version(
    version_id: int,
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    version = session.get(Version, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="version not found")
    package_name = version.package_name
    session.delete(version)
    session.commit()
    rebuild_repo(session)
    return RedirectResponse(f"/admin/apps/{package_name}", status_code=303)


@router.post("/keys")
def create_key(
    request: Request,
    label: str = Form(...),
    scope: str = Form(...),
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    scopes = [item.strip() for item in scope.split(",") if item.strip()]
    created = create_api_key(session, label, scopes, created_by=admin)
    keys = session.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    apps = session.scalars(select(App).order_by(App.package_name)).all()
    return templates.TemplateResponse(
        request,
        "admin/index.html",
        {"apps": apps, "keys": keys, "new_secret": created.secret},
    )


@router.post("/keys/{key_id}/revoke")
def revoke_key(
    key_id: int,
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    api_key = session.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.revoked = True
    session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/rebuild")
def rebuild(admin: str = Depends(require_admin), session: Session = Depends(get_session)):
    rebuild_repo(session)
    return RedirectResponse("/admin", status_code=303)


@router.get("/audit", response_class=HTMLResponse)
def audit(
    request: Request,
    admin: str = Depends(require_admin),
    session: Session = Depends(get_session),
):
    rows = session.scalars(select(AuditLog).order_by(AuditLog.ts.desc()).limit(200)).all()
    return templates.TemplateResponse(request, "admin/audit.html", {"rows": rows})


@router.get("/login")
async def login(request: Request):
    if not oidc_enabled():
        return RedirectResponse("/admin", status_code=303)
    client = oidc_client()
    redirect_uri = str(request.url_for("oidc_callback"))
    return await client.authorize_redirect(request, redirect_uri, code_challenge_method="S256")


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request):
    client = oidc_client()
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await client.userinfo(token=token)
    subject = userinfo.get("sub") or userinfo.get("email")
    if not subject:
        raise HTTPException(status_code=401, detail="OIDC subject missing")
    request.session["admin_user"] = subject
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout")
def logout(request: Request, admin: str = Depends(require_admin)):
    request.session.clear()
    return RedirectResponse("/admin", status_code=303)
