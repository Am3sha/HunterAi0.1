"""TLS hygiene scanner plugin.

Read-only, HTTP-observable TLS checks (no socket/cipher inspection in Milestone 3):
- a plaintext HTTP service that does NOT redirect to HTTPS         -> MEDIUM
- an HTTPS service with no HSTS header                             -> LOW
- an HTTPS service with a weak HSTS max-age (< 6 months)           -> LOW

Deeper TLS analysis (cipher suites, certificate validation, protocol versions)
is deliberately out of scope for this milestone.
"""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import limited_services, safe_get
from app.infrastructure.scanner.registry import register_plugin

_REF = "https://owasp.org/www-project-secure-headers/#http-strict-transport-security"
_MIN_HSTS_MAX_AGE = 15_552_000  # 6 months in seconds


def _hsts_max_age(value: str) -> int | None:
    for part in value.split(";"):
        part = part.strip().lower()
        if part.startswith("max-age="):
            try:
                return int(part.split("=", 1)[1])
            except ValueError:
                return None
    return None


@register_plugin
class TlsHygieneScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="tls-hygiene",
        title="TLS hygiene",
        description="Flags plaintext HTTP without redirect and weak/absent HSTS.",
        category=PluginCategory.MISCONFIGURATION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []
        findings: list[Finding] = []

        for service in limited_services(context.services):
            response = safe_get(context.http, service.url)
            if response is None:
                continue

            if not response.is_https:
                # Did the plaintext request end up on HTTPS (i.e. a redirect)?
                if not response.url.lower().startswith("https://"):
                    findings.append(
                        self.build_finding(
                            name="Plaintext HTTP without HTTPS redirect",
                            severity=Severity.MEDIUM,
                            target=response.url,
                            description=(
                                "The service is served over plaintext HTTP and does not "
                                "redirect to HTTPS."
                            ),
                            confidence=Confidence.HIGH,
                            evidence=f"GET {service.url} stayed on {response.url}",
                            references=[_REF],
                            metadata={"scheme": "http", "redirects_to_https": "false"},
                        )
                    )
                continue

            # HTTPS: assess HSTS.
            hsts = response.headers.get("strict-transport-security")
            if hsts is None:
                findings.append(self._hsts_issue(response.url, "absent", "HSTS header absent"))
                continue
            max_age = _hsts_max_age(hsts)
            if max_age is None or max_age < _MIN_HSTS_MAX_AGE:
                findings.append(
                    self._hsts_issue(
                        response.url,
                        "weak",
                        f"HSTS max-age too low (max-age={max_age})",
                    )
                )

        return findings

    def _hsts_issue(self, url: str, state: str, evidence: str) -> Finding:
        return self.build_finding(
            name="Weak or missing HSTS" if state == "weak" else "Missing HSTS",
            severity=Severity.LOW,
            target=url,
            description="HTTPS service has weak or absent Strict-Transport-Security.",
            confidence=Confidence.HIGH,
            evidence=f"{evidence} on {url}",
            references=[_REF],
            metadata={"hsts": state},
        )
