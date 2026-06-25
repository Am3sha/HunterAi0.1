"""StartScanUseCase — create a target + scan and schedule background recon.

Returns immediately with a RUNNING scan; the actual pipeline runs via the
injected ScanRunner. This keeps the API non-blocking.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.application.ports import ScanRunner
from app.domain.entities.scan import Scan
from app.domain.entities.target import Target
from app.domain.ports.persistence import ScanRepository, TargetRepository

logger = get_logger(__name__)


class StartScanUseCase:
    def __init__(
        self,
        target_repository: TargetRepository,
        scan_repository: ScanRepository,
        runner: ScanRunner,
    ) -> None:
        self._targets = target_repository
        self._scans = scan_repository
        self._runner = runner

    def execute(self, raw_domain: str) -> Scan:
        """Validate the domain, persist target + RUNNING scan, schedule recon."""
        target = Target.create(raw_domain)  # raises ValueError on invalid input
        self._targets.add(target)

        scan = Scan.create(target.id, target.domain)
        scan.mark_running()
        self._scans.add(scan)

        self._runner.run_in_background(scan.id)
        logger.info("Scheduled scan %s for %s", scan.id, target.domain)
        return scan
