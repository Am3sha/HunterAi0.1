"""RunReconUseCase — orchestrates the Subfinder → httpx → Katana pipeline.

This is pure application logic: it depends only on domain entities and the recon
stage ports. It knows the *order* of recon and how data flows between stages, but
nothing about subprocesses, JSON formats, or HTTP.

Flow:
    1. enumerate subdomains for the target domain
    2. probe (subdomains ∪ {apex}) for live HTTP services
    3. crawl the live service URLs for endpoints

Failures in any stage mark the scan FAILED while preserving partial results.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.domain.entities.scan import Scan
from app.domain.entities.target import Target
from app.domain.ports.recon import EndpointCrawler, HttpProber, SubdomainEnumerator

logger = get_logger(__name__)

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunReconUseCase:
    """Runs the reconnaissance pipeline for a target and returns a Scan."""

    def __init__(
        self,
        enumerator: SubdomainEnumerator,
        prober: HttpProber,
        crawler: EndpointCrawler,
        *,
        clock: Clock = _utcnow,
    ) -> None:
        self._enumerator = enumerator
        self._prober = prober
        self._crawler = crawler
        self._clock = clock

    def execute(self, target: Target, scan: Scan | None = None) -> Scan:
        """Run recon for ``target``.

        If ``scan`` is provided (e.g. an already-persisted RUNNING scan), results
        are attached to it; otherwise a new Scan is created. Either way the same
        Scan is returned with a terminal status.
        """
        if scan is None:
            scan = Scan.create(target.id, target.domain, now=self._clock())
        scan.mark_running(now=self._clock())
        logger.info("Recon started for %s (scan=%s)", target.domain, scan.id)

        try:
            self._enumerate(scan, target.domain)
            self._probe(scan, target.domain)
            self._crawl(scan)
        except Exception as exc:  # noqa: BLE001 - convert any stage failure to FAILED
            scan.mark_failed(str(exc), now=self._clock())
            logger.exception("Recon failed for %s (scan=%s)", target.domain, scan.id)
            return scan

        scan.mark_completed(now=self._clock())
        logger.info("Recon completed for %s: %s", target.domain, scan.counts)
        return scan

    # -- stages ---------------------------------------------------------------
    def _enumerate(self, scan: Scan, domain: str) -> None:
        scan.subdomains = self._enumerator.enumerate(domain)
        logger.info("Found %d subdomain(s)", len(scan.subdomains))

    def _probe(self, scan: Scan, domain: str) -> None:
        # Always include the apex domain, even if enumeration missed it.
        hosts = sorted({s.host for s in scan.subdomains} | {domain})
        scan.services = self._prober.probe(hosts)
        logger.info("Found %d live service(s) from %d host(s)", len(scan.services), len(hosts))

    def _crawl(self, scan: Scan) -> None:
        urls = [s.url for s in scan.services]
        if not urls:
            logger.info("No live services to crawl; skipping endpoint discovery")
            return
        scan.endpoints = self._crawler.crawl(urls)
        logger.info("Found %d endpoint(s)", len(scan.endpoints))
