"""Tool Executor — runs a tool binary safely and returns a structured result.

Implements ``ToolExecutorPort``. Deliberately small for Sprint 0:
- never uses a shell (args are passed as a list);
- always applies a timeout;
- captures stdout/stderr and wall-clock duration.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from app.core.logging import get_logger
from app.domain.entities.tool import ToolExecutionResult
from app.infrastructure.tools.errors import ToolExecutionError, ToolTimeoutError

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 300.0  # seconds


class ToolExecutor:
    """Runs external executables without a shell."""

    def __init__(self, default_timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._default_timeout = default_timeout

    def run(
        self,
        executable: Path,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        input_text: str | None = None,
    ) -> ToolExecutionResult:
        if not executable.exists():
            raise ToolExecutionError(f"Executable not found: {executable}")

        command = [str(executable), *args]
        effective_timeout = timeout if timeout is not None else self._default_timeout
        logger.debug("Executing: %s (timeout=%ss)", " ".join(command), effective_timeout)

        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolTimeoutError(
                f"{executable.name} timed out after {effective_timeout}s"
            ) from exc
        except OSError as exc:
            raise ToolExecutionError(f"Failed to execute {executable}: {exc}") from exc

        duration = time.monotonic() - started
        return ToolExecutionResult(
            command=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            duration_seconds=duration,
        )
