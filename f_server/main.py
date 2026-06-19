from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from f_server.config import get_settings
from f_server.db import create_all
from f_server.routers import admin, repo, upload


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="f-server", version="0.1.0")
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

    return app


app = create_app()
