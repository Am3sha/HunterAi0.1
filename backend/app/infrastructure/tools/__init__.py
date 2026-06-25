"""Tool Management subsystem: Registry, Provider, Manager, Executor.

Public API::

    from app.infrastructure.tools import ToolManager, build_tool_manager

The four pillars:
- ``ToolRegistry``  — declarative catalog of supported tools (pinned versions).
- ``ToolProvider``  — downloads + checksum-verifies + extracts a binary.
- ``ToolManager``   — orchestrates discovery / install / update / status / run.
- ``ToolExecutor``  — runs a binary safely (no shell, timeout, captured output).
"""

from __future__ import annotations

from app.infrastructure.tools.executor import ToolExecutor
from app.infrastructure.tools.factory import build_tool_manager
from app.infrastructure.tools.manager import ToolManager
from app.infrastructure.tools.models import (
    BinarySource,
    InstalledTool,
    ToolSpec,
    ToolStatus,
)
from app.infrastructure.tools.provider import GitHubReleaseProvider, ToolProvider
from app.infrastructure.tools.registry import ToolRegistry

__all__ = [
    "BinarySource",
    "GitHubReleaseProvider",
    "InstalledTool",
    "ToolExecutor",
    "ToolManager",
    "ToolProvider",
    "ToolRegistry",
    "ToolSpec",
    "ToolStatus",
    "build_tool_manager",
]
