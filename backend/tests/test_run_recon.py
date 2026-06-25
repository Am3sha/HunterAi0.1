"""Tests for RunReconUseCase orchestration (with fake stage adapters)."""

from __future__ import annotations

from collections.abc import Sequence

from app.application.use_cases.run_recon import RunReconUseCase
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.domain.entities.scan import ScanStatus
from app.domain.entities.target import Target


class _FakeEnumerator:
    def __init__(self, subs: list[Subdomain]) -> None:
        self._subs = subs

    def enumerate(self, domain: str) -> list[Subdomain]:
        return self._subs


class _FakeProber:
    def __init__(self, services: list[HttpService]) -> None:
        self._services = services
        self.seen_hosts: list[str] = []

    def probe(self, hosts: Sequence[str]) -> list[HttpService]:
        self.seen_hosts = list(hosts)
        return self._services


class _FakeCrawler:
    def __init__(self, endpoints: list[Endpoint]) -> None:
        self._endpoints = endpoints
        self.seen_urls: list[str] = []

    def crawl(self, urls: Sequence[str]) -> list[Endpoint]:
        self.seen_urls = list(urls)
        return self._endpoints


def _target() -> Target:
    return Target.create("example.com")


def test_happy_path_completes_with_results() -> None:
    enumerator = _FakeEnumerator([Subdomain("api.example.com"), Subdomain("www.example.com")])
    prober = _FakeProber([HttpService(url="https://www.example.com", status_code=200)])
    crawler = _FakeCrawler([Endpoint(url="https://www.example.com/login")])

    scan = RunReconUseCase(enumerator, prober, crawler).execute(_target())

    assert scan.status is ScanStatus.COMPLETED
    assert scan.counts == {"subdomains": 2, "services": 1, "endpoints": 1, "findings": 0}
    assert scan.started_at is not None and scan.finished_at is not None
    # Apex domain is always included in the probe set.
    assert "example.com" in prober.seen_hosts
    assert "api.example.com" in prober.seen_hosts
    # Only live service URLs are crawled.
    assert crawler.seen_urls == ["https://www.example.com"]


def test_no_live_services_skips_crawl() -> None:
    enumerator = _FakeEnumerator([Subdomain("api.example.com")])
    prober = _FakeProber([])
    crawler = _FakeCrawler([Endpoint(url="should-not-appear")])

    scan = RunReconUseCase(enumerator, prober, crawler).execute(_target())

    assert scan.status is ScanStatus.COMPLETED
    assert scan.endpoints == []
    assert crawler.seen_urls == []


def test_stage_failure_marks_failed_and_preserves_partial_results() -> None:
    class _BoomProber:
        def probe(self, hosts: Sequence[str]) -> list[HttpService]:
            raise RuntimeError("httpx blew up")

    enumerator = _FakeEnumerator([Subdomain("api.example.com")])
    scan = RunReconUseCase(enumerator, _BoomProber(), _FakeCrawler([])).execute(_target())

    assert scan.status is ScanStatus.FAILED
    assert scan.error is not None and "httpx blew up" in scan.error
    assert len(scan.subdomains) == 1  # partial result preserved
    assert scan.services == []
