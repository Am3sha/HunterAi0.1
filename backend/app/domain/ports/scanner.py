"""Port for vulnerability scanner plugins.

``ScannerPlugin`` is the single contract every plugin implements. The scanner
engine depends only on this Protocol — never on concrete plugins — which is what
lets new scanners be added without modifying the engine (dependency inversion).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.entities.finding import Finding
from app.domain.entities.scanner import PluginMetadata, ScanContext


@runtime_checkable
class ScannerPlugin(Protocol):
    """A self-contained vulnerability check."""

    metadata: PluginMetadata

    def scan(self, context: ScanContext) -> list[Finding]:
        """Inspect the attack surface and return any findings (possibly empty)."""
        ...
