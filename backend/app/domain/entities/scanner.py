"""Scanner domain models: plugin metadata, scan context, and engine results.

These are pure value objects shared by the scanner engine (application layer) and
the plugin implementations (infrastructure). They carry no framework or I/O
dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from app.domain.entities.finding import Finding, Severity
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.domain.entities.scanner_config import ScannerConfig

if TYPE_CHECKING:
    from app.domain.entities.scan import Scan
    from app.domain.ports.http import HttpClient
    from app.domain.ports.tools import ToolManagerPort


class PluginCategory(str, Enum):
    """Coarse classification of what a plugin looks for."""

    MISCONFIGURATION = "misconfiguration"
    INFORMATION_DISCLOSURE = "information_disclosure"
    INJECTION = "injection"
    ACCESS_CONTROL = "access_control"
    GENERIC = "generic"


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Static description of a scanner plugin (its identity and defaults)."""

    name: str
    """Stable unique identifier, e.g. ``"security-headers"``."""
    title: str
    description: str = ""
    category: PluginCategory = PluginCategory.GENERIC
    version: str = "0.1.0"
    default_enabled: bool = True


@dataclass(frozen=True, slots=True)
class ScanContext:
    """The attack surface handed to each plugin.

    Built from reconnaissance output. Plugins read what they need (services,
    endpoints, ...) and decide what to test. Immutable so plugins cannot affect
    each other through shared state.
    """

    target_domain: str
    services: tuple[HttpService, ...] = ()
    endpoints: tuple[Endpoint, ...] = ()
    subdomains: tuple[Subdomain, ...] = ()
    http: "HttpClient | None" = field(default=None, compare=False)
    """Shared, scope-enforcing, read-only HTTP client. ``None`` => no live
    requests available (plugins must degrade gracefully)."""
    tools: "ToolManagerPort | None" = field(default=None, compare=False)
    """Shared managed-tool runner (e.g. for future ffuf-based plugins). ``None``
    => tool execution unavailable (plugins must degrade gracefully)."""
    config: ScannerConfig = field(default_factory=ScannerConfig, compare=False)
    """Per-scan limits/timeouts. Defaults match historical behaviour."""

    @property
    def service_urls(self) -> list[str]:
        return [service.url for service in self.services]

    @property
    def endpoint_urls(self) -> list[str]:
        return [endpoint.url for endpoint in self.endpoints]

    def parameterized_endpoints(self) -> list[Endpoint]:
        """Endpoints whose URL carries a query string (``?a=b``).

        Convenience for future plugins that test request parameters. Purely a
        view over existing data — no requests, no payloads.
        """
        return [e for e in self.endpoints if "?" in e.url and e.url.split("?", 1)[1]]

    @classmethod
    def from_scan(
        cls,
        scan: "Scan",
        http: "HttpClient | None" = None,
        *,
        tools: "ToolManagerPort | None" = None,
        config: ScannerConfig | None = None,
    ) -> "ScanContext":
        """Build a context from a recon Scan's results."""
        return cls(
            target_domain=scan.target_domain,
            services=tuple(scan.services),
            endpoints=tuple(scan.endpoints),
            subdomains=tuple(scan.subdomains),
            http=http,
            tools=tools,
            config=config or ScannerConfig(),
        )


class PluginRunStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PluginExecution:
    """Record of one plugin's execution within an engine run."""

    plugin: str
    status: PluginRunStatus
    findings: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ScanEngineResult:
    """Aggregated output of a scanner engine run."""

    findings: tuple[Finding, ...]
    executions: tuple[PluginExecution, ...]

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def counts_by_severity(self) -> dict[str, int]:
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    @property
    def failed_plugins(self) -> list[str]:
        return [e.plugin for e in self.executions if e.status is PluginRunStatus.FAILED]

    def sorted_findings(self) -> list[Finding]:
        """Findings ordered by severity, most severe first."""
        return sorted(self.findings, key=lambda f: f.severity.rank, reverse=True)
