"""Factory: assemble a ScannerEngine from the plugin registry."""

from __future__ import annotations

from collections.abc import Iterable

from app.application.use_cases.run_vulnerability_scan import ScannerEngine
from app.infrastructure.scanner.registry import ScannerRegistry, build_default_registry


def build_scanner_engine(
    *,
    enabled: Iterable[str] | None = None,
    disabled: Iterable[str] | None = None,
    registry: ScannerRegistry | None = None,
) -> ScannerEngine:
    """Build a ScannerEngine with the selected plugins.

    By default, discovers all registered plugins and selects those marked
    ``default_enabled``. Pass ``enabled``/``disabled`` to override, or a custom
    ``registry`` (e.g. in tests).
    """
    registry = registry or build_default_registry()
    plugins = registry.select(enabled=enabled, disabled=disabled)
    return ScannerEngine(plugins)
