"""Scans API.

- ``POST /scans``        create a scan, start recon in the background, return 202.
- ``GET  /scans``        list recent scans (summaries).
- ``GET  /scans/{id}``   current status + results (frontend polls this).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.ports import ScanRunner
from app.application.use_cases.start_scan import StartScanUseCase
from app.domain.ports.persistence import ScanRepository, TargetRepository
from app.interfaces.api.deps import (
    get_scan_repository,
    get_scan_runner,
    get_target_repository,
)
from app.interfaces.api.schemas.scan import (
    ScanCreatedResponse,
    ScanCreateRequest,
    ScanDetailResponse,
    ScanSummaryResponse,
)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_scan(
    payload: ScanCreateRequest,
    targets: TargetRepository = Depends(get_target_repository),
    scans: ScanRepository = Depends(get_scan_repository),
    runner: ScanRunner = Depends(get_scan_runner),
) -> ScanCreatedResponse:
    """Create a scan and kick off reconnaissance in the background."""
    try:
        scan = StartScanUseCase(targets, scans, runner).execute(payload.domain)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ScanCreatedResponse(
        scan_id=scan.id,
        status=scan.status.value,
        target_domain=scan.target_domain,
        created_at=scan.created_at,
    )


@router.get("", response_model=list[ScanSummaryResponse])
def list_scans(
    scans: ScanRepository = Depends(get_scan_repository),
) -> list[ScanSummaryResponse]:
    return [ScanSummaryResponse.from_domain(s) for s in scans.list()]


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan(
    scan_id: UUID,
    scans: ScanRepository = Depends(get_scan_repository),
) -> ScanDetailResponse:
    scan = scans.get(scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Scan {scan_id} not found")
    return ScanDetailResponse.from_domain(scan)
