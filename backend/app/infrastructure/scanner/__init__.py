"""Scanner subsystem: plugin-based vulnerability scanning framework.

Public API::

    from app.infrastructure.scanner import (
        BaseScannerPlugin,
        ScannerRegistry,
        build_scanner_engine,
        register_plugin,
    )

Pillars:
- ``ScannerPlugin`` (domain port)        — the plugin contract.
- ``ScannerEngine`` (application)        — orchestrates plugins, isolates failures.
- ``ScannerRegistry`` + ``register_plugin`` — discovery/registration of plugins.
- ``BaseScannerPlugin``                  — convenience base for writing plugins.
"""

from __future__ import annotations

from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.errors import (
    DuplicatePluginError,
    PluginNotFoundError,
    ScannerError,
)
from app.infrastructure.scanner.factory import build_scanner_engine
from app.infrastructure.scanner.registry import (
    ScannerRegistry,
    build_default_registry,
    discover_plugins,
    register_plugin,
)

__all__ = [
    "BaseScannerPlugin",
    "DuplicatePluginError",
    "PluginNotFoundError",
    "ScannerEngine",
    "ScannerError",
    "ScannerRegistry",
    "build_default_registry",
    "build_scanner_engine",
    "discover_plugins",
    "register_plugin",
]
