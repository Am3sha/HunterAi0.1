"""Database CLI — quick schema management for development.

    python -m app.db_cli init    # create all tables (dev convenience)
    python -m app.db_cli drop    # drop all tables

For production / schema evolution, prefer Alembic:
    alembic upgrade head
"""

from __future__ import annotations

import argparse

from app.core.logging import configure_logging, get_logger
from app.infrastructure.persistence.database import get_engine
from app.infrastructure.persistence.models import Base

logger = get_logger("db_cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hunterai-db", description="HunterAI DB management")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create all tables")
    sub.add_parser("drop", help="Drop all tables")
    args = parser.parse_args(argv)

    configure_logging()
    engine = get_engine()

    if args.command == "init":
        Base.metadata.create_all(engine)
        logger.info("Created all tables on %s", engine.url)
        return 0
    if args.command == "drop":
        Base.metadata.drop_all(engine)
        logger.info("Dropped all tables on %s", engine.url)
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
