"""Reflected XSS scanner plugin.

Safe, passive detection only: sends harmless reflection markers and checks for
unencoded reflection in response bodies. No exploitation, no bypasses, no
aggressive fuzzing. Uses the shared read-only HttpClient and parameter utilities.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import for_each_service_response, safe_get
from app.infrastructure.scanner.plugins._params import param_names, with_param_value
from app.infrastructure.scanner.registry import register_plugin

logger = get_logger(__name__)

# Harmless reflection markers - unique strings that won't trigger WAFs or cause issues
# These are not exploit payloads, just detectable markers for reflection testing
REFLECTION_MARKERS = (
    "hunterai_xss_marker_1",
    "hunterai_xss_marker_2",
)

# CVSS 3.1 for reflected XSS (AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N) = 6.1 MEDIUM
XSS_CVSS = Cvss(
    version="3.1",
    vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    base_score=6.1,
)


@register_plugin
class XssScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="xss",
        title="Reflected Cross-Site Scripting",
        description="Safe passive detection of reflected XSS via harmless reflection markers.",
        category=PluginCategory.INJECTION,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        if context.http is None:
            return []

        findings: list[Finding] = []
        endpoints = context.parameterized_endpoints()

        # Respect max_endpoints limit from ScannerConfig
        max_endpoints = context.config.max_endpoints
        endpoints = list(endpoints)[:max_endpoints]

        for endpoint in endpoints:
            self._test_endpoint(endpoint, context.http, findings)

        return findings

    def _test_endpoint(self, endpoint, http, findings: list[Finding]) -> None:
        """Test a single endpoint's parameters for reflection."""
        param_list = param_names(endpoint.url)
        if not param_list:
            return

        for param in param_list:
            for marker in REFLECTION_MARKERS:
                # Build test URL with marker injected into this parameter
                test_url = with_param_value(endpoint.url, param, marker)

                response = safe_get(http, test_url)
                if response is None:
                    continue  # Request failed/out of scope, skip

                # Check for unencoded reflection of our marker
                if self._is_reflected(response.body, marker):
                    findings.append(
                        self.build_finding(
                            name=f"Reflected XSS in parameter '{param}'",
                            severity=Severity.MEDIUM,
                            target=response.url,
                            description=(
                                f"Parameter '{param}' reflects user input without proper "
                                "encoding, allowing potential Cross-Site Scripting (XSS)."
                            ),
                            confidence=Confidence.MEDIUM,
                            evidence=(
                                f"Marker '{marker}' reflected unencoded in response body "
                                f"for URL: {test_url}"
                            ),
                            references=[
                                "https://owasp.org/www-community/attacks/xss/",
                                "https://cwe.mitre.org/data/definitions/79.html",
                            ],
                            cvss=XSS_CVSS,
                            cwe_ids=("CWE-79",),
                            owasp_categories=("A03:2021-Injection",),
                            remediation=(
                                "Contextually encode all user-controlled input when rendering "
                                "in HTML, JavaScript, CSS, or URL contexts. Implement a "
                                "Content Security Policy (CSP) as defense-in-depth."
                            ),
                            metadata={
                                "parameter": param,
                                "marker": marker,
                                "endpoint": endpoint.url,
                            },
                        )
                    )
                    # Only report once per parameter per endpoint
                    break

    def _is_reflected(self, body: str, marker: str) -> bool:
        """Check if marker appears unencoded in response body."""
        if not body or not marker:
            return False
        # Simple substring check - marker should appear exactly as sent (unencoded)
        return marker in body