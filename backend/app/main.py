"""FastAPI application factory and entrypoint.

Run with: ``uvicorn app.main:app --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks. Tool Manager + DB wiring attach here later."""
    settings: Settings = get_settings()
    logger.info("Starting %s (env=%s, debug=%s)", settings.app_name, settings.env, settings.debug)
    logger.info("Managed tools dir: %s", settings.tools_dir)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(debug=settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="AI-assisted bug bounty platform — authorized testing only.",
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Mount the versioned API.
    from app.interfaces.api.router import api_router

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Also expose /health unprefixed for simple liveness checks / load balancers.
    from app.interfaces.api.routes.health import router as health_router

    app.include_router(health_router)

    return app


app = create_app()
