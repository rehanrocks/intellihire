"""Builds the FastAPI application.

`uvicorn app.main:app` imports this module and serves the `app` object.
Everything is assembled inside create_app() so tests can build a fresh app
with different settings.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controller import admin, auth, company, users
from app.core.config import get_settings
from app.core.exceptions import AppError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup (before the first request) and once at shutdown.
    Path(get_settings().upload_dir).mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="IntelliHire backend. Module 1: authentication and account management.",
        lifespan=lifespan,
    )

    # CORS: which browser origins may call this API. "*" is fine while developing;
    # in production list the real frontend domain(s).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # One place turns every AppError raised anywhere into a JSON reply.
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/health", tags=["Health"], summary="Is the API up?")
    def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    for router in (auth.router, users.router, company.router, admin.router):
        app.include_router(router, prefix=settings.api_prefix)

    return app


app = create_app()
