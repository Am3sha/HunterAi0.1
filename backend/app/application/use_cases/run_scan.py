"""RunScanUseCase — full scan pipeline: reconnaissance then vulnerability scanning.

Composes the recon use case and the scanner engine. Pure application logic with
injected collaborators, so it is testable without real tools or a database.

Flow:
    1. run reconnaissance (RunReconUseCase) — populates services/endpoints/...
    2. if recon COMPLETED, build a ScanContext and run the ScannerEngine
    3. attach findings to the scan and re-stamp completion time

If recon FAILED, scanning is skipped and the failed scan is returned unchanged.
The ScannerEngine isolates individual plugin failures internally, so a bad plugin
never fails the scan.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.application.use_cases.run_recon import RunReconUseCase
from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.core.logging import get_logger
from app.domain.entities.scan import Scan, ScanStatus
from app.domain.entities.scanner import ScanContext
from app.domain.entities.target import Target
from app.domain.ports.http import HttpClient

logger = get_logger(__name__)

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunScanUseCase:
    """Runs recon, then the scanner engine, attaching findings to the scan."""

    def __init__(
        self,
        recon: RunReconUseCase,
        engine: ScannerEngine,
        *,
        http_client: HttpClient | None = None,
        clock: Clock = _utcnow,
    ) -> None:
        self._recon = recon
        self._engine = engine
        self._http_client = http_client
        self._clock = clock

    def execute(self, target: Target, scan: Scan | None = None) -> Scan:
        scan = self._recon.execute(target, scan=scan)
        if scan.status is not ScanStatus.COMPLETED:
            return scan  # recon failed; nothing to scan

        context = ScanContext.from_scan(scan, http=self._http_client)
        result = self._engine.run(context)
        scan.findings = list(result.findings)
        # Re-stamp completion to reflect the end of scanning (not just recon).
        scan.mark_completed(now=self._clock())
        logger.info(
            "Scan %s complete: %s finding(s) from %d plugin(s)",
            scan.id,
            len(scan.findings),
            len(self._engine.plugin_names),
        )
        return scan
