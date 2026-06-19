from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

    return app


app = create_app()
