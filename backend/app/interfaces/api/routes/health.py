"""Health & readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    env: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe. Confirms the service is up and reports basic metadata."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        env=settings.env,
    )
