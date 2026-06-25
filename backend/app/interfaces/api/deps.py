"""FastAPI dependency providers (wiring the composition root to endpoints)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import lru_cache
from uuid import UUID

from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.application.ports import ScanRunner
from app.domain.ports.persistence import ScanRepository, TargetRepository
from app.infrastructure.persistence.database import get_sessionmaker
from app.infrastructure.persistence.repositories import (
    SqlAlchemyScanRepository,
    SqlAlchemyTargetRepository,
)
from app.infrastructure.tools import ToolManager, build_tool_manager


@lru_cache
def get_tool_manager() -> ToolManager:
    """Provide a process-wide ToolManager."""
    return build_tool_manager()


def get_session() -> Iterator[Session]:
    """Yield a request-scoped database session."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def get_target_repository(session: Session = Depends(get_session)) -> TargetRepository:
    return SqlAlchemyTargetRepository(session)


def get_scan_repository(session: Session = Depends(get_session)) -> ScanRepository:
    return SqlAlchemyScanRepository(session)


def get_execute_scan() -> Callable[[UUID], None]:
    """Return the callable that runs a scan in the background.

    Imported lazily so importing the API never requires a configured database.
    Overridable in tests to avoid invoking real security tools.
    """
    from app.infrastructure.execution import execute_scan

    return execute_scan


def get_scan_runner(
    background_tasks: BackgroundTasks,
    execute: Callable[[UUID], None] = Depends(get_execute_scan),
) -> ScanRunner:
    from app.infrastructure.execution import BackgroundTasksScanRunner

    return BackgroundTasksScanRunner(background_tasks, execute)
