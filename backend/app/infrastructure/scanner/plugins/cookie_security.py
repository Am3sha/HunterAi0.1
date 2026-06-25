"""Cookie security scanner plugin.

Read-only: GETs each live service and inspects Set-Cookie headers for missing
Secure / HttpOnly / SameSite attributes.
"""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import for_each_service_response, iter_set_cookie
from app.infrastructure.scanner.registry import register_plugin

_REF = "https://owasp.org/www-community/controls/SecureCookieAttribute"


def _cookie_name(raw: str) -> str:
    return raw.split("=", 1)[0].strip() or "<unnamed>"


def _attributes(raw: str) -> set[str]:
    # Attributes are ';'-separated after the name=value pair.
    parts = raw.split(";")[1:]
    return {p.strip().lower().split("=", 1)[0] for p in parts if p.strip()}


@register_plugin
class CookieSecurityScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="cookie-security",
        title="Insecure cookie attributes",
        description="Flags cookies missing Secure / HttpOnly / SameSite attributes.",
        category=PluginCategory.MISCONFIGURATION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []
        findings: list[Finding] = []

        def handle(service, response) -> None:
            for raw in iter_set_cookie(response):
                name = _cookie_name(raw)
                attrs = _attributes(raw)
                # Secure is most important over HTTPS (cookie sent in cleartext otherwise).
                if response.is_https and "secure" not in attrs:
                    findings.append(
                        self._issue(response.url, name, "Secure", Severity.MEDIUM)
                    )
                if "httponly" not in attrs:
                    findings.append(
                        self._issue(response.url, name, "HttpOnly", Severity.LOW)
                    )
                if "samesite" not in attrs:
                    findings.append(
                        self._issue(response.url, name, "SameSite", Severity.LOW)
                    )

        for_each_service_response(context.http, context.services, handle)
        return findings

    def _issue(self, url: str, cookie: str, attribute: str, severity: Severity) -> Finding:
        return self.build_finding(
            name=f"Cookie '{cookie}' missing {attribute} attribute",
            severity=severity,
            target=url,
            description=f"The cookie '{cookie}' is set without the {attribute} attribute.",
            confidence=Confidence.HIGH,
            evidence=f"Set-Cookie for '{cookie}' lacks {attribute} on {url}",
            references=[_REF],
            metadata={"cookie": cookie, "attribute": attribute},
        )
