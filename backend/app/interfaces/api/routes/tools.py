"""Read-only tool status endpoint.

Exposes what the Tool Manager knows about required vs. installed tools. Useful for
the frontend to warn when setup hasn't been run. (Installation itself is done via
the ``hunterai-tools`` CLI, not the API.)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.infrastructure.tools import ToolManager
from app.interfaces.api.deps import get_tool_manager

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolStatusResponse(BaseModel):
    name: str
    required_version: str
    installed: bool
    installed_version: str | None = None
    needs_install: bool


@router.get("", response_model=list[ToolStatusResponse])
def list_tools(manager: ToolManager = Depends(get_tool_manager)) -> list[ToolStatusResponse]:
    """Return required vs. installed status for every registered tool."""
    return [
        ToolStatusResponse(
            name=s.name,
            required_version=s.required_version,
            installed=s.installed,
            installed_version=s.installed_version,
            needs_install=s.needs_install,
        )
        for s in manager.status()
    ]
