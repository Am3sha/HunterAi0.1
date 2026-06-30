"""Vulnerability finding — the output unit of a scanner plugin.

Pure domain value objects. A Finding describes a single issue a plugin reports
against a specific target (URL/host/endpoint). Severity is ordered so findings
can be ranked and summarised without the consumer knowing the scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Numeric ordering (higher = more severe)."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Cvss:
    """A CVSS score attached to a finding.

    Immutable value object. ``severity`` is intentionally NOT derived from this in
    Milestone 2 — severity remains the plugin's decision until the Sprint 2 M6 risk
    scoring engine.
    """

    version: str
    """CVSS version, e.g. ``"3.1"``."""
    vector: str
    """The CVSS vector string, e.g. ``"CVSS:3.1/AV:N/AC:L/..."``."""
    base_score: float
    """The CVSS base score (0.0–10.0)."""


@dataclass(frozen=True, slots=True)
class Finding:
    """A single issue reported by a scanner plugin."""

    plugin: str
    """Name of the plugin that produced this finding."""
    name: str
    severity: Severity
    target: str
    """What the finding is about — typically a URL, host, or endpoint."""
    description: str = ""
    confidence: Confidence = Confidence.MEDIUM
    evidence: str | None = None
    references: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    # --- Advanced classification (Sprint 2 M2; all optional, default empty) ---
    cvss: Cvss | None = None
    cwe_ids: tuple[str, ...] = ()
    """Mapped CWE identifiers, e.g. ``("CWE-79",)``. Usually one, but multiple
    mappings are supported without a future migration."""
    owasp_categories: tuple[str, ...] = ()
    """Mapped OWASP categories, e.g. ``("A03:2021-Injection",)``."""
    remediation: str | None = None
    """Free-text remediation guidance."""
