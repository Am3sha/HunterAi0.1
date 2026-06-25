"""Ports (interfaces) for the Tool Management subsystem.

These Protocols define the *narrow* surface the application layer needs:
- resolve / ensure a tool's executable is present
- run a tool and get a structured result

Concrete implementations live in ``app.infrastructure.tools``. Keeping the
interface here means use cases never import infrastructure.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.domain.entities.tool import ToolExecutionResult


class ToolExecutorPort(Protocol):
    """Runs an executable safely and returns a structured result."""

    def run(
        self,
        executable: Path,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        input_text: str | None = None,
    ) -> ToolExecutionResult: ...


class ToolManagerPort(Protocol):
    """Resolves and runs managed tools by logical name (e.g. ``"subfinder"``)."""

    def ensure_installed(self, name: str) -> Path:
        """Return the executable path, installing it first if necessary."""
        ...

    def resolve_path(self, name: str) -> Path:
        """Return the executable path for an already-installed tool."""
        ...

    def run(
        self,
        name: str,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        input_text: str | None = None,
    ) -> ToolExecutionResult:
        """Ensure the tool is installed, then execute it."""
        ...
