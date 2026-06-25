"""Clickjacking protection scanner plugin.

Read-only: GETs each live service and verifies anti-framing protection. A page is
protected if it sends either ``X-Frame-Options`` (DENY/SAMEORIGIN) or a CSP with a
``frame-ancestors`` directive. This plugin owns framing checks so the
security-headers plugin can stay non-overlapping.
"""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import for_each_service_response
from app.infrastructure.scanner.registry import register_plugin

_REF = "https://owasp.org/www-community/attacks/Clickjacking"


def _has_frame_ancestors(csp: str | None) -> bool:
    return csp is not None and "frame-ancestors" in csp.lower()


@register_plugin
class ClickjackingScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="clickjacking",
        title="Missing clickjacking protection",
        description="Flags pages lacking X-Frame-Options and CSP frame-ancestors.",
        category=PluginCategory.MISCONFIGURATION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []
        findings: list[Finding] = []

        def handle(service, response) -> None:
            xfo = response.headers.get("x-frame-options")
            csp = response.headers.get("content-security-policy")
            if xfo is None and not _has_frame_ancestors(csp):
                findings.append(
                    self.build_finding(
                        name="Missing clickjacking protection",
                        severity=Severity.MEDIUM,
                        target=response.url,
                        description=(
                            "No X-Frame-Options header and no CSP 'frame-ancestors' "
                            "directive; the page may be framed (clickjacking)."
                        ),
                        confidence=Confidence.HIGH,
                        evidence=f"Neither X-Frame-Options nor frame-ancestors on {response.url}",
                        references=[_REF],
                        metadata={"x_frame_options": "absent", "frame_ancestors": "absent"},
                    )
                )

        for_each_service_response(context.http, context.services, handle)
        return findings
