"""Execution backend for scans.

``BackgroundTasksScanRunner`` implements the ``ScanRunner`` port using FastAPI's
BackgroundTasks. ``execute_scan`` is the composition root for a single background
run: it owns its own DB session (the request's session is already closed), loads
the persisted scan, runs the recon pipeline, and saves the results.

To swap the backend later (Celery/RQ/...), provide a new ScanRunner that enqueues
``execute_scan`` elsewhere — the API contract and use cases stay unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import BackgroundTasks

from app.application.use_cases.run_recon import RunReconUseCase
from app.application.use_cases.run_scan import RunScanUseCase
from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.core.logging import get_logger
from app.domain.entities.http import TargetScope
from app.domain.entities.target import Target
from app.infrastructure.http import build_scoped_http_client
from app.infrastructure.persistence.database import get_sessionmaker
from app.infrastructure.persistence.repositories import SqlAlchemyScanRepository
from app.infrastructure.recon import build_recon_pipeline
from app.infrastructure.scanner import build_scanner_engine
from app.infrastructure.tools import build_tool_manager

logger = get_logger(__name__)


def _build_scanner_engine() -> ScannerEngine:
    """Build the scanner engine, degrading to an empty engine on discovery error.

    A failure to load plugins must never discard successful recon results.
    """
    try:
        return build_scanner_engine()
    except Exception:  # noqa: BLE001 - resilience: recon results must survive
        logger.exception("Failed to build scanner engine; continuing with no plugins")
        return ScannerEngine([])


class BackgroundTasksScanRunner:
    """Schedules scan execution via FastAPI BackgroundTasks."""

    def __init__(
        self,
        background_tasks: BackgroundTasks,
        execute: Callable[[UUID], None],
    ) -> None:
        self._background_tasks = background_tasks
        self._execute = execute

    def run_in_background(self, scan_id: UUID) -> None:
        self._background_tasks.add_task(self._execute, scan_id)


def execute_scan(scan_id: UUID) -> None:
    """Run recon + vulnerability scanning for a persisted scan and store results."""
    session = get_sessionmaker()()
    repo = SqlAlchemyScanRepository(session)
    try:
        scan = repo.get(scan_id)
        if scan is None:
            logger.warning("execute_scan: scan %s not found", scan_id)
            return

        target = Target(
            id=scan.target_id, domain=scan.target_domain, created_at=scan.created_at
        )
        recon = RunReconUseCase(*build_recon_pipeline(build_tool_manager()))
        http_client = build_scoped_http_client(TargetScope.from_hosts({scan.target_domain}))
        RunScanUseCase(
            recon, _build_scanner_engine(), http_client=http_client
        ).execute(target, scan=scan)
        repo.update(scan)
        logger.info("execute_scan: scan %s finished as %s", scan_id, scan.status.value)
    except Exception:  # noqa: BLE001 - last-resort guard around the whole run
        logger.exception("execute_scan: unexpected failure for scan %s", scan_id)
        try:
            scan = repo.get(scan_id)
            if scan is not None:
                scan.mark_failed("Internal error while running the scan")
                repo.update(scan)
        except Exception:  # noqa: BLE001
            logger.exception("execute_scan: failed to record failure for %s", scan_id)
    finally:
        session.close()
