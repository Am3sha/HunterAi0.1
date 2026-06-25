"""Request/response schemas for the scans API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.scan import Scan


class ScanCreateRequest(BaseModel):
    domain: str = Field(..., examples=["example.com"], description="Root domain to scan")


class ScanCreatedResponse(BaseModel):
    scan_id: UUID
    status: str
    target_domain: str
    created_at: datetime


class SubdomainOut(BaseModel):
    host: str
    source: str | None = None


class HttpServiceOut(BaseModel):
    url: str
    input: str | None = None
    status_code: int | None = None
    title: str | None = None
    webserver: str | None = None
    content_length: int | None = None
    host: str | None = None
    technologies: list[str] = []


class EndpointOut(BaseModel):
    url: str
    method: str | None = None
    source: str | None = None


class FindingOut(BaseModel):
    id: UUID
    plugin: str
    name: str
    severity: str
    target: str
    description: str = ""
    confidence: str
    evidence: str | None = None
    references: list[str] = []
    metadata: dict[str, str] = {}


class ScanSummaryResponse(BaseModel):
    scan_id: UUID
    target_domain: str
    status: str
    counts: dict[str, int]
    created_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def from_domain(cls, scan: Scan) -> "ScanSummaryResponse":
        return cls(
            scan_id=scan.id,
            target_domain=scan.target_domain,
            status=scan.status.value,
            counts=scan.counts,
            created_at=scan.created_at,
            finished_at=scan.finished_at,
        )


class ScanDetailResponse(ScanSummaryResponse):
    error: str | None = None
    started_at: datetime | None = None
    subdomains: list[SubdomainOut] = []
    services: list[HttpServiceOut] = []
    endpoints: list[EndpointOut] = []
    findings: list[FindingOut] = []

    @classmethod
    def from_domain(cls, scan: Scan) -> "ScanDetailResponse":
        return cls(
            scan_id=scan.id,
            target_domain=scan.target_domain,
            status=scan.status.value,
            counts=scan.counts,
            created_at=scan.created_at,
            started_at=scan.started_at,
            finished_at=scan.finished_at,
            error=scan.error,
            subdomains=[SubdomainOut(host=s.host, source=s.source) for s in scan.subdomains],
            services=[
                HttpServiceOut(
                    url=s.url,
                    input=s.input,
                    status_code=s.status_code,
                    title=s.title,
                    webserver=s.webserver,
                    content_length=s.content_length,
                    host=s.host,
                    technologies=list(s.technologies),
                )
                for s in scan.services
            ],
            endpoints=[
                EndpointOut(url=e.url, method=e.method, source=e.source) for e in scan.endpoints
            ],
            findings=[
                FindingOut(
                    id=f.id,
                    plugin=f.plugin,
                    name=f.name,
                    severity=f.severity.value,
                    target=f.target,
                    description=f.description,
                    confidence=f.confidence.value,
                    evidence=f.evidence,
                    references=list(f.references),
                    metadata=dict(f.metadata),
                )
                for f in scan.findings
            ],
        )
