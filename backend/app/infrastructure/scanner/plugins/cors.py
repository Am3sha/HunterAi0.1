"""CORS misconfiguration scanner plugin.

Read-only: sends a GET with a benign probe ``Origin`` header and inspects the
CORS response headers. This is header inspection, NOT payload injection — we only
observe how the server reflects an Origin.

Detections:
- reflects the arbitrary probe Origin AND allows credentials  -> HIGH
- reflects the arbitrary probe Origin (no credentials)        -> MEDIUM
- Access-Control-Allow-Origin: *  AND allows credentials      -> HIGH (invalid+risky)
- Access-Control-Allow-Origin: *  (no credentials)            -> LOW (informational)
"""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import limited_services, safe_get
from app.infrastructure.scanner.registry import register_plugin

# A clearly third-party, non-routable origin (.invalid TLD per RFC 2606).
_PROBE_ORIGIN = "https://hunterai-cors-probe.invalid"
_REF = "https://portswigger.net/web-security/cors"


@register_plugin
class CorsScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="cors-misconfig",
        title="CORS misconfiguration",
        description="Detects overly permissive CORS via a benign Origin probe.",
        category=PluginCategory.MISCONFIGURATION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []
        findings: list[Finding] = []

        for service in limited_services(context.services):
            response = safe_get(context.http, service.url, headers={"Origin": _PROBE_ORIGIN})
            if response is None:
                continue
            acao = response.headers.get("access-control-allow-origin")
            if acao is None:
                continue
            creds = (response.headers.get("access-control-allow-credentials", "") or "").lower()
            allows_creds = creds == "true"
            finding = self._evaluate(response.url, acao.strip(), allows_creds)
            if finding is not None:
                findings.append(finding)

        return findings

    def _evaluate(self, url: str, acao: str, allows_creds: bool) -> Finding | None:
        if acao == _PROBE_ORIGIN:
            severity = Severity.HIGH if allows_creds else Severity.MEDIUM
            detail = "reflects an arbitrary Origin"
            if allows_creds:
                detail += " with credentials allowed"
            return self._issue(url, detail, acao, allows_creds, severity)
        if acao == "*":
            if allows_creds:
                # ACAO:* with credentials is invalid but, where honoured, dangerous.
                return self._issue(
                    url, "uses wildcard Origin with credentials allowed", acao, True, Severity.HIGH
                )
            return self._issue(
                url, "allows any Origin (wildcard)", acao, False, Severity.LOW
            )
        return None

    def _issue(
        self, url: str, detail: str, acao: str, allows_creds: bool, severity: Severity
    ) -> Finding:
        return self.build_finding(
            name=f"CORS policy {detail}",
            severity=severity,
            target=url,
            description=f"The endpoint {detail}.",
            confidence=Confidence.HIGH if allows_creds else Confidence.MEDIUM,
            evidence=(
                f"Origin: {_PROBE_ORIGIN} -> Access-Control-Allow-Origin: {acao}, "
                f"Access-Control-Allow-Credentials: {str(allows_creds).lower()}"
            ),
            references=[_REF],
            metadata={"allow_origin": acao, "allow_credentials": str(allows_creds).lower()},
        )
