"""Application-layer ports.

``ScanRunner`` abstracts *how* a scan's recon pipeline is executed in the
background. Sprint 0 implements it with FastAPI BackgroundTasks; later it can be
swapped for Celery/RQ/etc. without changing the API or use cases.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ScanRunner(Protocol):
    def run_in_background(self, scan_id: UUID) -> None:
        """Schedule reconnaissance for an already-persisted scan."""
        ...
