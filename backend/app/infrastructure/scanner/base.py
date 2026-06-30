"""BaseScannerPlugin — optional convenience base class for plugins.

Plugins only need to satisfy the ``ScannerPlugin`` Protocol, but subclassing this
base gives them:
- a class-level ``metadata`` slot (validated at subclass creation), and
- a ``build_finding`` helper that stamps the plugin name automatically.

A plugin author writes one file under ``infrastructure/scanner/plugins/`` and
decorates the class with ``@register_plugin`` — no other code changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import ClassVar

from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.scanner import PluginMetadata, ScanContext


class BaseScannerPlugin(ABC):
    """Convenience base for scanner plugins."""

    metadata: ClassVar[PluginMetadata]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Allow intermediate abstract bases without metadata; concrete plugins
        # are validated by the registry when registered/instantiated.
        meta = getattr(cls, "metadata", None)
        if meta is not None and not isinstance(meta, PluginMetadata):
            raise TypeError(
                f"{cls.__name__}.metadata must be a PluginMetadata instance"
            )

    @abstractmethod
    def scan(self, context: ScanContext) -> list[Finding]:
        """Inspect the attack surface and return findings (possibly empty)."""
        raise NotImplementedError

    def build_finding(
        self,
        *,
        name: str,
        severity: Severity,
        target: str,
        description: str = "",
        confidence: Confidence = Confidence.MEDIUM,
        evidence: str | None = None,
        references: Iterable[str] = (),
        metadata: Mapping[str, str] | None = None,
        cvss: Cvss | None = None,
        cwe_ids: Iterable[str] = (),
        owasp_categories: Iterable[str] = (),
        remediation: str | None = None,
    ) -> Finding:
        """Construct a Finding with this plugin's name pre-filled."""
        return Finding(
            plugin=self.metadata.name,
            name=name,
            severity=severity,
            target=target,
            description=description,
            confidence=confidence,
            evidence=evidence,
            references=tuple(references),
            metadata=dict(metadata or {}),
            cvss=cvss,
            cwe_ids=tuple(cwe_ids),
            owasp_categories=tuple(owasp_categories),
            remediation=remediation,
        )
