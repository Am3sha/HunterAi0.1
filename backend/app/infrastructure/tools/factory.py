"""Factory for building a configured ToolManager from application settings."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.infrastructure.tools.manager import ToolManager


def build_tool_manager(settings: Settings | None = None) -> ToolManager:
    """Construct a ToolManager rooted at the configured managed tools directory."""
    settings = settings or get_settings()
    settings.tools_dir.mkdir(parents=True, exist_ok=True)
    return ToolManager(tools_dir=settings.tools_dir)
