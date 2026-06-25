"""Domain value object for the result of running an external tool.

Pure data — no framework or subprocess imports. The application layer (recon use
case in Milestone 3) depends on this type, not on any concrete executor.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """Outcome of a single tool invocation."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        """True when the process exited successfully."""
        return self.returncode == 0

    def stdout_lines(self) -> list[str]:
        """Non-empty, stripped stdout lines (recon tools emit one item per line)."""
        return [line.strip() for line in self.stdout.splitlines() if line.strip()]
