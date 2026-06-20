from __future__ import annotations

import io
import subprocess
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

import qrcode
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from qrcode.image.svg import SvgPathImage
from starlette.middleware.sessions import SessionMiddleware

from f_server.config import get_settings
from f_server.db import create_all
from f_server.routers import admin, repo, upload


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="f-server", version="0.1.0")
    templates = Jinja2Templates(directory="f_server/templates")
    app.add_middleware(SessionMiddleware, secret_key=settings.admin_auth.session_secret)
    app.mount("/static", StaticFiles(directory="f_server/static"), name="static")
    app.include_router(repo.router)
    app.include_router(upload.router)
    app.include_router(admin.router)

    @app.on_event("startup")
    def _startup() -> None:
        create_all()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse("f_server/static/favicon.ico")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "repo_name": settings.repo.name,
                "repo_description": settings.repo.description,
            },
        )

    @app.get("/add-repository", response_class=HTMLResponse)
    def add_repository(request: Request):
        repo_add_url = _repo_add_url(settings)
        return templates.TemplateResponse(
            request,
            "add_repository.html",
            {
                "repo_name": settings.repo.name,
                "repo_description": settings.repo.description,
                "repo_add_url": repo_add_url,
            },
        )

    @app.get("/add-repository.svg")
    def add_repository_qr():
        image = qrcode.make(_repo_add_url(settings), image_factory=SvgPathImage)
        out = io.BytesIO()
        image.save(out)
        return Response(content=out.getvalue(), media_type="image/svg+xml")

    return app


app = create_app()


def _repo_add_url(settings) -> str:
    repo_url = settings.repo.url.rstrip("/")
    fingerprint = _repo_signing_fingerprint(settings)
    if not fingerprint:
        return repo_url
    parts = urlsplit(repo_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["fingerprint"] = fingerprint
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _repo_signing_fingerprint(settings) -> str | None:
    repo = settings.repo
    if not (repo.keystore_path and repo.keystore_pass and repo.key_alias and repo.key_pass):
        return None
    try:
        result = subprocess.run(
            [
                "keytool",
                "-list",
                "-v",
                "-keystore",
                str(repo.keystore_path),
                "-storepass",
                repo.keystore_pass,
                "-alias",
                repo.key_alias,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in result.stdout.splitlines():
        if "SHA256:" in line:
            return line.split("SHA256:", 1)[1].strip().replace(":", "").upper()
    return None
