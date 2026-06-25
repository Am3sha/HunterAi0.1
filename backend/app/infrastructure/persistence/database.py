"""Database engine and session factory (synchronous SQLAlchemy).

Sync (not async) is a deliberate Sprint 0 choice: the recon pipeline shells out
to blocking subprocesses and runs in a thread (FastAPI BackgroundTasks / threadpool
endpoints), so a sync session is simpler and correct. The engine is created lazily
so importing this module never requires a configured database.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _initialize() -> None:
    global _engine, _SessionLocal
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "HUNTERAI_DATABASE_URL is not set. Configure it in .env "
            "(e.g. postgresql+psycopg://hunterai:hunterai@localhost:5432/hunterai)."
        )
    _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    _SessionLocal = sessionmaker(
        bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )


def get_engine() -> Engine:
    if _engine is None:
        _initialize()
    assert _engine is not None
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    if _SessionLocal is None:
        _initialize()
    assert _SessionLocal is not None
    return _SessionLocal
