"""Aggregate API router.

Individual route modules are included here, then mounted under the versioned
prefix by the app factory. New resources (targets, scans, ...) plug in here.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.routes import health, scans, tools

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tools.router)
api_router.include_router(scans.router)
