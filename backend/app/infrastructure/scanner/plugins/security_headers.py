"""Security headers scanner plugin.

Read-only: GETs each live service and flags missing HTTP security headers. Does
NOT check X-Frame-Options / frame-ancestors — that is the clickjacking plugin's
responsibility (kept separate so plugins stay independent and non-overlapping).
"""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import for_each_service_response
from app.infrastructure.scanner.registry import register_plugin

# header -> (human title, severity, reference)
_CHECKS: dict[str, tuple[str, Severity, str]] = {
    "strict-transport-security": (
        "Strict-Transport-Security (HSTS)",
        Severity.LOW,
        "https://owasp.org/www-project-secure-headers/#http-strict-transport-security",
    ),
    "content-security-policy": (
        "Content-Security-Policy",
        Severity.LOW,
        "https://owasp.org/www-project-secure-headers/#content-security-policy",
    ),
    "x-content-type-options": (
        "X-Content-Type-Options",
        Severity.LOW,
        "https://owasp.org/www-project-secure-headers/#x-content-type-options",
    ),
    "referrer-policy": (
        "Referrer-Policy",
        Severity.INFO,
        "https://owasp.org/www-project-secure-headers/#referrer-policy",
    ),
    "permissions-policy": (
        "Permissions-Policy",
        Severity.INFO,
        "https://owasp.org/www-project-secure-headers/#permissions-policy",
    ),
}


@register_plugin
class SecurityHeadersScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="security-headers",
        title="Missing security headers",
        description="Flags absent recommended HTTP security headers.",
        category=PluginCategory.MISCONFIGURATION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []
        findings: list[Finding] = []

        def handle(service, response) -> None:
            # HSTS is only meaningful over HTTPS.
            for header, (title, severity, ref) in _CHECKS.items():
                if header == "strict-transport-security" and not response.is_https:
                    continue
                if not response.headers.has(header):
                    findings.append(
                        self.build_finding(
                            name=f"Missing {title}",
                            severity=severity,
                            target=response.url,
                            description=f"The response does not set the {title} header.",
                            confidence=Confidence.HIGH,
                            evidence=f"{header} header absent on {response.url}",
                            references=[ref],
                            metadata={"header": header},
                        )
                    )

        for_each_service_response(context.http, context.services, handle)
        return findings
