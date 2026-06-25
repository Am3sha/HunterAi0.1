"""Logging setup.

A single ``configure_logging`` call wires up a sensible default logger. Kept
deliberately small for Sprint 0; structured/JSON logging can be added later
without touching call sites.
"""

from __future__ import annotations

import logging

_CONFIGURED = False


def configure_logging(debug: bool = False) -> None:
    """Configure root logging once. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (e.g. ``get_logger(__name__)``)."""
    return logging.getLogger(f"hunterai.{name}")
