"""End-to-end API tests for the scans endpoints.

Uses in-memory SQLite (shared via StaticPool) and a fake background executor, so
no real security tools run. Verifies the create -> poll contract.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.entities.finding import Finding, Severity
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.repositories import SqlAlchemyScanRepository
from app.interfaces.api.deps import get_execute_scan, get_session
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_session():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    def fake_execute(scan_id: UUID) -> None:
        session = TestSession()
        try:
            repo = SqlAlchemyScanRepository(session)
            scan = repo.get(scan_id)
            if scan is None:
                return
            scan.subdomains = [Subdomain("api.example.com", "subfinder")]
            scan.services = [HttpService(url="https://example.com", status_code=200)]
            scan.endpoints = [Endpoint("https://example.com/login", "GET", "katana")]
            scan.findings = [
                Finding(
                    plugin="security-headers",
                    name="Missing CSP",
                    severity=Severity.MEDIUM,
                    target="https://example.com",
                )
            ]
            scan.mark_completed()
            repo.update(scan)
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_execute_scan] = lambda: fake_execute
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_returns_202_running_and_normalizes_domain(client) -> None:
    resp = client.post("/api/v1/scans", json={"domain": "HTTPS://Example.com/"})
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "running"
    assert body["target_domain"] == "example.com"
    assert UUID(body["scan_id"])


def test_create_then_poll_until_completed(client) -> None:
    sid = client.post("/api/v1/scans", json={"domain": "example.com"}).json()["scan_id"]
    # TestClient runs background tasks before returning, so it is already done.
    resp = client.get(f"/api/v1/scans/{sid}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "completed"
    assert detail["counts"] == {
        "subdomains": 1,
        "services": 1,
        "endpoints": 1,
        "findings": 1,
    }
    assert detail["services"][0]["status_code"] == 200
    assert detail["endpoints"][0]["method"] == "GET"
    assert detail["findings"][0]["plugin"] == "security-headers"
    assert detail["findings"][0]["severity"] == "medium"


def test_invalid_domain_returns_422(client) -> None:
    resp = client.post("/api/v1/scans", json={"domain": "not a domain"})
    assert resp.status_code == 422


def test_unknown_scan_returns_404(client) -> None:
    resp = client.get(f"/api/v1/scans/{uuid4()}")
    assert resp.status_code == 404


def test_list_scans(client) -> None:
    client.post("/api/v1/scans", json={"domain": "example.com"})
    resp = client.get("/api/v1/scans")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
