"""SQLAlchemy repository implementations + domain<->ORM mapping."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.domain.entities.scan import Scan, ScanStatus
from app.domain.entities.target import Target
from app.infrastructure.persistence.models import (
    EndpointModel,
    FindingModel,
    HttpServiceModel,
    ScanModel,
    SubdomainModel,
    TargetModel,
)


class SqlAlchemyTargetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, target: Target) -> None:
        self._session.add(
            TargetModel(id=target.id, domain=target.domain, created_at=target.created_at)
        )
        self._session.commit()


class SqlAlchemyScanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scan: Scan) -> None:
        model = ScanModel(
            id=scan.id,
            target_id=scan.target_id,
            target_domain=scan.target_domain,
            status=scan.status.value,
            error=scan.error,
            created_at=scan.created_at,
            started_at=scan.started_at,
            finished_at=scan.finished_at,
        )
        self._apply_results(model, scan)
        self._session.add(model)
        self._session.commit()

    def update(self, scan: Scan) -> None:
        model = self._session.get(ScanModel, scan.id)
        if model is None:
            # Treat an update to an unknown scan as an insert (defensive).
            self.add(scan)
            return
        model.status = scan.status.value
        model.error = scan.error
        model.started_at = scan.started_at
        model.finished_at = scan.finished_at
        self._apply_results(model, scan)
        self._session.commit()

    def get(self, scan_id: UUID) -> Scan | None:
        model = self._session.get(ScanModel, scan_id)
        return _to_domain(model) if model is not None else None

    def list(self, limit: int = 50) -> list[Scan]:
        stmt = select(ScanModel).order_by(ScanModel.created_at.desc()).limit(limit)
        return [_to_domain(m) for m in self._session.scalars(stmt).all()]

    # -- helpers --------------------------------------------------------------
    @staticmethod
    def _apply_results(model: ScanModel, scan: Scan) -> None:
        """Replace the model's child collections with the scan's results."""
        model.subdomains = [
            SubdomainModel(host=s.host, source=s.source) for s in scan.subdomains
        ]
        model.services = [
            HttpServiceModel(
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
        ]
        model.endpoints = [
            EndpointModel(url=e.url, method=e.method, source=e.source) for e in scan.endpoints
        ]
        model.findings = [
            FindingModel(
                uid=f.id,
                plugin=f.plugin,
                name=f.name,
                severity=f.severity.value,
                target=f.target,
                description=f.description,
                confidence=f.confidence.value,
                evidence=f.evidence,
                references=list(f.references),
                meta=dict(f.metadata),
                cvss_version=f.cvss.version if f.cvss else None,
                cvss_vector=f.cvss.vector if f.cvss else None,
                cvss_base_score=f.cvss.base_score if f.cvss else None,
                cwe_ids=list(f.cwe_ids),
                owasp_categories=list(f.owasp_categories),
                remediation=f.remediation,
            )
            for f in scan.findings
        ]


def _to_domain(model: ScanModel) -> Scan:
    return Scan(
        id=model.id,
        target_id=model.target_id,
        target_domain=model.target_domain,
        status=ScanStatus(model.status),
        subdomains=[Subdomain(host=s.host, source=s.source) for s in model.subdomains],
        services=[
            HttpService(
                url=s.url,
                input=s.input,
                status_code=s.status_code,
                title=s.title,
                webserver=s.webserver,
                content_length=s.content_length,
                host=s.host,
                technologies=tuple(s.technologies or ()),
            )
            for s in model.services
        ],
        endpoints=[
            Endpoint(url=e.url, method=e.method, source=e.source) for e in model.endpoints
        ],
        findings=[
            Finding(
                id=f.uid,
                plugin=f.plugin,
                name=f.name,
                severity=Severity(f.severity),
                target=f.target,
                description=f.description or "",
                confidence=Confidence(f.confidence),
                evidence=f.evidence,
                references=tuple(f.references or ()),
                metadata=dict(f.meta or {}),
                cvss=Cvss(version=f.cvss_version, vector=f.cvss_vector, base_score=f.cvss_base_score)
                if f.cvss_version and f.cvss_vector and f.cvss_base_score is not None
                else None,
                cwe_ids=tuple(f.cwe_ids or ()),
                owasp_categories=tuple(f.owasp_categories or ()),
                remediation=f.remediation,
            )
            for f in model.findings
        ],
        error=model.error,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )
