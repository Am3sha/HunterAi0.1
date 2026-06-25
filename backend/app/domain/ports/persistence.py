"""Persistence ports — repository interfaces owned by the domain.

Implemented by the infrastructure layer (SQLAlchemy). Use cases depend on these
Protocols, never on the concrete repositories.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.scan import Scan
from app.domain.entities.target import Target


class TargetRepository(Protocol):
    def add(self, target: Target) -> None: ...


class ScanRepository(Protocol):
    def add(self, scan: Scan) -> None:
        """Persist a newly created scan (typically with no results yet)."""
        ...

    def get(self, scan_id: UUID) -> Scan | None:
        """Load a scan and its results, or None if not found."""
        ...

    def update(self, scan: Scan) -> None:
        """Persist status/timestamp changes and (re)store the scan's results."""
        ...

    def list(self, limit: int = 50) -> list[Scan]:
        """Return recent scans (most recent first)."""
        ...
