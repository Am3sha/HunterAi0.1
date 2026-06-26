"""ScannerConfig — injectable limits/timeouts for a scan run.

A small, immutable value object carrying the knobs that were previously module
constants in ``infrastructure/scanner/plugins/_http.py``. Defaults are identical to
the current behaviour, so injecting a default ``ScannerConfig`` changes nothing.

It is exposed to plugins via ``ScanContext.config`` (with a default applied), which
lets future milestones make scans configurable without touching plugins.
"""

from __future__ import annotations

from dataclasses import dataclass

# Defaults mirror the existing constants in scanner/plugins/_http.py exactly.
DEFAULT_REQUEST_TIMEOUT = 5.0
DEFAULT_MAX_SERVICES = 25
DEFAULT_MAX_ENDPOINTS = 50


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    """Per-scan limits and timeouts shared by plugins."""

    request_timeout: float = DEFAULT_REQUEST_TIMEOUT
    max_services: int = DEFAULT_MAX_SERVICES
    max_endpoints: int = DEFAULT_MAX_ENDPOINTS
