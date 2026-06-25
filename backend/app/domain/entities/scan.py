"""Scan entity — one reconnaissance run against a target.

A Scan is a small state machine (PENDING → RUNNING → COMPLETED | FAILED) that
also aggregates the results of each recon stage. The use case in the application
layer drives the transitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.domain.entities.finding import Finding
from app.domain.entities.recon import Endpoint, HttpService, Subdomain


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Scan:
    """A reconnaissance run and its accumulated results."""

    id: UUID
    target_id: UUID
    target_domain: str
    status: ScanStatus = ScanStatus.PENDING
    subdomains: list[Subdomain] = field(default_factory=list)
    services: list[HttpService] = field(default_factory=list)
    endpoints: list[Endpoint] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None

    # -- factory --------------------------------------------------------------
    @classmethod
    def create(cls, target_id: UUID, target_domain: str, *, now: datetime | None = None) -> "Scan":
        created = now or datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            target_id=target_id,
            target_domain=target_domain,
            status=ScanStatus.PENDING,
            created_at=created,
        )

    # -- transitions ----------------------------------------------------------
    def mark_running(self, *, now: datetime | None = None) -> None:
        self.status = ScanStatus.RUNNING
        self.started_at = now or datetime.now(timezone.utc)

    def mark_completed(self, *, now: datetime | None = None) -> None:
        self.status = ScanStatus.COMPLETED
        self.finished_at = now or datetime.now(timezone.utc)

    def mark_failed(self, error: str, *, now: datetime | None = None) -> None:
        self.status = ScanStatus.FAILED
        self.error = error
        self.finished_at = now or datetime.now(timezone.utc)

    # -- convenience ----------------------------------------------------------
    @property
    def counts(self) -> dict[str, int]:
        return {
            "subdomains": len(self.subdomains),
            "services": len(self.services),
            "endpoints": len(self.endpoints),
            "findings": len(self.findings),
        }
