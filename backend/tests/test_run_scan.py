"""Tests for RunScanUseCase — recon + scanner engine integration (with fakes)."""

from __future__ import annotations

from collections.abc import Sequence

from app.application.use_cases.run_recon import RunReconUseCase
from app.application.use_cases.run_scan import RunScanUseCase
from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.domain.entities.finding import Finding, Severity
from app.domain.entities.recon import HttpService, Subdomain
from app.domain.entities.scan import ScanStatus
from app.domain.entities.scanner import PluginMetadata, ScanContext
from app.domain.entities.target import Target


class _FakeEnumerator:
    def enumerate(self, domain: str) -> list[Subdomain]:
        return [Subdomain("www.example.com")]


class _FakeProber:
    def probe(self, hosts: Sequence[str]) -> list[HttpService]:
        return [HttpService(url="https://www.example.com", status_code=200)]


class _FakeCrawler:
    def crawl(self, urls: Sequence[str]) -> list:
        return []


class _CountingPlugin:
    """Emits one finding per service in the context."""

    def __init__(self) -> None:
        self.metadata = PluginMetadata(name="counter", title="counter")
        self.seen_context: ScanContext | None = None

    def scan(self, context: ScanContext) -> list[Finding]:
        self.seen_context = context
        return [
            Finding(plugin="counter", name="svc", severity=Severity.LOW, target=s.url)
            for s in context.services
        ]


def _recon() -> RunReconUseCase:
    return RunReconUseCase(_FakeEnumerator(), _FakeProber(), _FakeCrawler())


def _target() -> Target:
    return Target.create("example.com")


def test_scan_runs_engine_after_recon_and_attaches_findings() -> None:
    plugin = _CountingPlugin()
    use_case = RunScanUseCase(_recon(), ScannerEngine([plugin]))

    scan = use_case.execute(_target())

    assert scan.status is ScanStatus.COMPLETED
    assert len(scan.findings) == 1
    assert scan.findings[0].plugin == "counter"
    assert scan.counts["findings"] == 1
    # The engine received the recon results as its attack surface.
    assert plugin.seen_context is not None
    assert plugin.seen_context.service_urls == ["https://www.example.com"]


def test_scan_with_no_plugins_completes_without_findings() -> None:
    scan = RunScanUseCase(_recon(), ScannerEngine([])).execute(_target())
    assert scan.status is ScanStatus.COMPLETED
    assert scan.findings == []


def test_scan_skips_scanning_when_recon_fails() -> None:
    class _BoomEnumerator:
        def enumerate(self, domain: str) -> list[Subdomain]:
            raise RuntimeError("subfinder down")

    plugin = _CountingPlugin()
    recon = RunReconUseCase(_BoomEnumerator(), _FakeProber(), _FakeCrawler())
    scan = RunScanUseCase(recon, ScannerEngine([plugin])).execute(_target())

    assert scan.status is ScanStatus.FAILED
    assert scan.findings == []
    assert plugin.seen_context is None  # engine never ran
