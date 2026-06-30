"""Repository round-trip tests on in-memory SQLite."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.domain.entities.scan import Scan, ScanStatus
from app.domain.entities.target import Target
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.repositories import (
    SqlAlchemyScanRepository,
    SqlAlchemyTargetRepository,
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_scan_create_then_update_with_results(session_factory) -> None:
    session = session_factory()
    targets = SqlAlchemyTargetRepository(session)
    scans = SqlAlchemyScanRepository(session)

    target = Target.create("example.com")
    targets.add(target)

    scan = Scan.create(target.id, target.domain)
    scan.mark_running()
    scans.add(scan)

    loaded = scans.get(scan.id)
    assert loaded is not None
    assert loaded.status is ScanStatus.RUNNING
    assert loaded.counts == {"subdomains": 0, "services": 0, "endpoints": 0, "findings": 0}

    # Complete the scan with results and persist.
    scan.subdomains = [Subdomain("api.example.com", "subfinder")]
    scan.services = [
        HttpService(url="https://example.com", status_code=200, technologies=("nginx",))
    ]
    scan.endpoints = [Endpoint("https://example.com/login", "GET", "katana")]
    scan.findings = [
        Finding(
            plugin="security-headers",
            name="Missing CSP",
            severity=Severity.MEDIUM,
            target="https://example.com",
            description="No Content-Security-Policy header",
            confidence=Confidence.HIGH,
            evidence="header absent",
            references=("https://owasp.org/csp",),
            metadata={"header": "content-security-policy"},
        )
    ]
    scan.mark_completed()
    scans.update(scan)

    reloaded = scans.get(scan.id)
    assert reloaded is not None
    assert reloaded.status is ScanStatus.COMPLETED
    assert reloaded.counts == {"subdomains": 1, "services": 1, "endpoints": 1, "findings": 1}
    assert reloaded.services[0].technologies == ("nginx",)
    assert reloaded.endpoints[0].method == "GET"
    finding = reloaded.findings[0]
    assert finding.id == scan.findings[0].id
    assert finding.plugin == "security-headers"
    assert finding.severity is Severity.MEDIUM
    assert finding.confidence is Confidence.HIGH
    assert finding.references == ("https://owasp.org/csp",)
    assert finding.metadata == {"header": "content-security-policy"}


def test_finding_advanced_fields_round_trip(session_factory) -> None:
    session = session_factory()
    targets = SqlAlchemyTargetRepository(session)
    scans = SqlAlchemyScanRepository(session)

    target = Target.create("example.com")
    targets.add(target)
    scan = Scan.create(target.id, target.domain)
    scans.add(scan)

    cvss = Cvss(version="3.1", vector="CVSS:3.1/AV:N/AC:L", base_score=7.5)
    scan.findings = [
        Finding(
            plugin="xss",
            name="Reflected XSS",
            severity=Severity.HIGH,
            target="https://example.com/search?q=test",
            cvss=cvss,
            cwe_ids=("CWE-79", "CWE-80"),
            owasp_categories=("A03:2021-Injection",),
            remediation="Contextually encode all user input.",
        )
    ]
    scan.mark_completed()
    scans.update(scan)

    reloaded = scans.get(scan.id)
    assert reloaded is not None
    f = reloaded.findings[0]
    assert f.cvss is not None
    assert f.cvss.version == "3.1"
    assert f.cvss.vector == "CVSS:3.1/AV:N/AC:L"
    assert f.cvss.base_score == 7.5
    assert f.cwe_ids == ("CWE-79", "CWE-80")
    assert f.owasp_categories == ("A03:2021-Injection",)
    assert f.remediation == "Contextually encode all user input."


def test_get_missing_returns_none(session_factory) -> None:
    from uuid import uuid4

    scans = SqlAlchemyScanRepository(session_factory())
    assert scans.get(uuid4()) is None


def test_list_orders_recent_first(session_factory) -> None:
    session = session_factory()
    targets = SqlAlchemyTargetRepository(session)
    scans = SqlAlchemyScanRepository(session)
    for domain in ("a.com", "b.com"):
        target = Target.create(domain)
        targets.add(target)
        scan = Scan.create(target.id, target.domain)
        scans.add(scan)

    listed = scans.list()
    assert len(listed) == 2
