"""SQL Injection scanner plugin — error-based detection only.

Safe, passive detection only: injects benign syntax markers and checks for
database error messages in response bodies. No exploitation, no time-based
payloads, no UNION attacks, no data extraction. Uses the shared read-only
HttpClient and parameter utilities.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.plugins._http import safe_get
from app.infrastructure.scanner.plugins._params import param_names, with_param_value
from app.infrastructure.scanner.registry import register_plugin

logger = get_logger(__name__)

# Benign syntax markers that may trigger DB errors in responses (not exploit payloads)
ERROR_MARKERS = (
    "'",           # Unclosed single quote
    "''",          # Double single quote
    '"',           # Double quote
    "`",           # Backtick (MySQL identifier quoting)
)

# DB-specific error signatures (lowercase for case-insensitive matching)
DB_ERROR_SIGNATURES = {
    "mysql": (
        "you have an error in your sql syntax",
        "mysql_fetch",
        "mysqli_",
        "mysql_num_rows",
        "mysql_result",
        "supplied argument is not a valid mysql",
        "unknown column",
        "unknown table",
        "column count doesn't match",
    ),
    "postgresql": (
        "syntax error at or near",
        "pg_query",
        "pg_exec",
        "pg_fetch",
        "postgresql",
        "unterminated quoted string",
        "invalid input syntax for type",
    ),
    "sqlserver": (
        "unclosed quotation mark",
        "microsoft ole db",
        "odbc",
        "sqlserver",
        "incorrect syntax near",
        "unexpected end of query",
    ),
    "oracle": (
        "ora-009",
        "ora-017",
        "pls-",
        "oracle error",
        "oracle driver",
    ),
    "sqlite": (
        "sqlite3.operationalerror",
        "near \"\" syntax error",
        "sqlite_error",
        "unrecognized token",
    ),
}

# CVSS 3.1 for Potential SQL Injection (error-based signal only)
# AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N = 5.3 MEDIUM
# Provisional until active verification confirms exploitation.
SQLI_CVSS = Cvss(
    version="3.1",
    vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N",
    base_score=5.3,
)


@register_plugin
class SqliScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="sqli",
        title="Error-Based SQL Injection",
        description="Safe passive detection of potential SQL injection via benign syntax markers.",
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
        """Test a single endpoint's parameters for SQL error reflection."""
        param_list = param_names(endpoint.url)
        if not param_list:
            return

        for param in param_list:
            for marker in ERROR_MARKERS:
                # Build test URL with marker injected into this parameter
                test_url = with_param_value(endpoint.url, param, marker)

                response = safe_get(http, test_url)
                if response is None:
                    continue  # Request failed/out of scope, skip

                # Check for database error messages in response body
                db_type = self._identify_db_error(response.body)
                if db_type:
                    findings.append(
                        self.build_finding(
                            name=f"Potential SQL Injection in parameter '{param}'",
                            severity=Severity.MEDIUM,
                            target=response.url,
                            description=(
                                f"Parameter '{param}' triggers database error messages "
                                f"({db_type}), indicating potential SQL Injection."
                            ),
                            confidence=Confidence.MEDIUM,
                            evidence=(
                                f"Marker '{marker}' caused {db_type} error in response body "
                                f"for URL: {test_url}"
                            ),
                            references=[
                                "https://owasp.org/www-community/attacks/SQL_Injection",
                                "https://cwe.mitre.org/data/definitions/89.html",
                            ],
                            cvss=SQLI_CVSS,
                            cwe_ids=("CWE-89",),
                            owasp_categories=("A03:2021-Injection",),
                            remediation=(
                                "Use parameterized queries (prepared statements) for all "
                                "database interactions. Validate and sanitize all user input. "
                                "Implement least-privilege database accounts. Disable verbose "
                                "error messages in production."
                            ),
                            metadata={
                                "parameter": param,
                                "marker": marker,
                                "endpoint": endpoint.url,
                                "db_type": db_type,
                            },
                        )
                    )
                    # Only report once per parameter per endpoint
                    break

    def _identify_db_error(self, body: str) -> str | None:
        """Identify database type from error messages in response body."""
        if not body:
            return None
        lower_body = body.lower()
        for db_type, signatures in DB_ERROR_SIGNATURES.items():
            for sig in signatures:
                if sig in lower_body:
                    return db_type
        return None