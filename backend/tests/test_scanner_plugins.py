"""Tests for the seven Milestone-3 scanner plugins."""

from __future__ import annotations

from app.domain.entities.finding import Confidence, Cvss, Finding, Severity
from app.domain.entities.scanner import ScanContext, ScannerConfig
from app.infrastructure.scanner.plugins.clickjacking import ClickjackingScanner
from app.infrastructure.scanner.plugins.cookie_security import CookieSecurityScanner
from app.infrastructure.scanner.plugins.cors import CorsScanner, _PROBE_ORIGIN
from app.infrastructure.scanner.plugins.security_headers import SecurityHeadersScanner
from app.infrastructure.scanner.plugins.tls_hygiene import TlsHygieneScanner
from app.infrastructure.scanner.plugins.xss import XssScanner, REFLECTION_MARKERS
from app.infrastructure.scanner.plugins.sqli import SqliScanner, ERROR_MARKERS
from app.infrastructure.scanner.plugins._params import with_param_value
from tests.scanner_fakes import FakeHttpClient, context_for, response

URL = "https://example.com"


def _names(findings):
    return [f.name for f in findings]


# --- shared behaviour --------------------------------------------------------
def test_plugins_noop_without_http_client() -> None:
    ctx = ScanContext(target_domain="example.com")  # http=None
    for plugin in (
        SecurityHeadersScanner(),
        CookieSecurityScanner(),
        CorsScanner(),
        ClickjackingScanner(),
        TlsHygieneScanner(),
        XssScanner(),
        SqliScanner(),
    ):
        assert plugin.scan(ctx) == []


def test_failed_request_yields_no_findings_not_an_exception() -> None:
    # Empty canned map => every request raises HttpClientError internally.
    client = FakeHttpClient({})
    ctx = context_for([URL], client)
    # Must not raise; just produces nothing.
    assert SecurityHeadersScanner().scan(ctx) == []
    assert XssScanner().scan(ctx) == []
    assert SqliScanner().scan(ctx) == []


# --- security headers --------------------------------------------------------
def test_security_headers_flags_missing_headers() -> None:
    client = FakeHttpClient({URL: response(URL)})  # no security headers at all
    findings = SecurityHeadersScanner().scan(context_for([URL], client))
    names = _names(findings)
    assert "Missing Strict-Transport-Security (HSTS)" in names
    assert "Missing Content-Security-Policy" in names
    assert "Missing X-Content-Type-Options" in names


def test_security_headers_present_no_findings() -> None:
    headers = [
        ("Strict-Transport-Security", "max-age=63072000"),
        ("Content-Security-Policy", "default-src 'self'"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Permissions-Policy", "geolocation=()"),
    ]
    client = FakeHttpClient({URL: response(URL, headers=headers)})
    assert SecurityHeadersScanner().scan(context_for([URL], client)) == []


def test_security_headers_skips_hsts_on_http() -> None:
    http_url = "http://example.com"
    client = FakeHttpClient({http_url: response(http_url)})
    names = _names(SecurityHeadersScanner().scan(context_for([http_url], client)))
    assert "Missing Strict-Transport-Security (HSTS)" not in names  # HSTS only on https


# --- cookie security ---------------------------------------------------------
def test_cookie_security_flags_missing_attributes() -> None:
    client = FakeHttpClient({URL: response(URL, headers=[("Set-Cookie", "sid=abc; Path=/")])})
    findings = CookieSecurityScanner().scan(context_for([URL], client))
    names = _names(findings)
    assert "Cookie 'sid' missing Secure attribute" in names
    assert "Cookie 'sid' missing HttpOnly attribute" in names
    assert "Cookie 'sid' missing SameSite attribute" in names
    assert any(f.severity is Severity.MEDIUM for f in findings)  # Secure on https


def test_cookie_security_well_configured_cookie() -> None:
    cookie = "sid=abc; Secure; HttpOnly; SameSite=Strict"
    client = FakeHttpClient({URL: response(URL, headers=[("Set-Cookie", cookie)])})
    assert CookieSecurityScanner().scan(context_for([URL], client)) == []


# --- CORS --------------------------------------------------------------------
def test_cors_reflected_origin_with_credentials_is_high() -> None:
    headers = [
        ("Access-Control-Allow-Origin", _PROBE_ORIGIN),
        ("Access-Control-Allow-Credentials", "true"),
    ]
    client = FakeHttpClient({URL: response(URL, headers=headers)})
    findings = CorsScanner().scan(context_for([URL], client))
    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH


def test_cors_wildcard_without_credentials_is_low() -> None:
    client = FakeHttpClient({URL: response(URL, headers=[("Access-Control-Allow-Origin", "*")])})
    findings = CorsScanner().scan(context_for([URL], client))
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW


def test_cors_no_acao_no_finding() -> None:
    client = FakeHttpClient({URL: response(URL)})
    assert CorsScanner().scan(context_for([URL], client)) == []


# --- clickjacking ------------------------------------------------------------
def test_clickjacking_flags_unprotected_page() -> None:
    client = FakeHttpClient({URL: response(URL)})
    findings = ClickjackingScanner().scan(context_for([URL], client))
    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM


def test_clickjacking_protected_by_xfo() -> None:
    client = FakeHttpClient({URL: response(URL, headers=[("X-Frame-Options", "DENY")])})
    assert ClickjackingScanner().scan(context_for([URL], client)) == []


def test_clickjacking_protected_by_csp_frame_ancestors() -> None:
    headers = [("Content-Security-Policy", "frame-ancestors 'none'")]
    client = FakeHttpClient({URL: response(URL, headers=headers)})
    assert ClickjackingScanner().scan(context_for([URL], client)) == []


# --- TLS hygiene -------------------------------------------------------------
def test_tls_plaintext_without_redirect_is_medium() -> None:
    http_url = "http://example.com"
    client = FakeHttpClient({http_url: response(http_url, requested_url=http_url)})
    findings = TlsHygieneScanner().scan(context_for([http_url], client))
    assert len(findings) == 1
    assert findings[0].severity is Severity.MEDIUM


def test_tls_http_redirecting_to_https_is_clean() -> None:
    http_url = "http://example.com"
    # request started on http, final url is https (redirect) + strong HSTS
    resp = response(
        "https://example.com",
        headers=[("Strict-Transport-Security", "max-age=63072000")],
        requested_url=http_url,
    )
    client = FakeHttpClient({http_url: resp})
    assert TlsHygieneScanner().scan(context_for([http_url], client)) == []


def test_tls_https_missing_hsts_is_low() -> None:
    client = FakeHttpClient({URL: response(URL)})
    findings = TlsHygieneScanner().scan(context_for([URL], client))
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW
    assert findings[0].metadata["hsts"] == "absent"


def test_tls_weak_hsts_max_age_is_low() -> None:
    client = FakeHttpClient({URL: response(URL, headers=[("Strict-Transport-Security", "max-age=100")])})
    findings = TlsHygieneScanner().scan(context_for([URL], client))
    assert len(findings) == 1
    assert findings[0].metadata["hsts"] == "weak"


# --- XSS (reflected) -----------------------------------------------------------
def test_xss_noop_without_http_client() -> None:
    ctx = ScanContext(target_domain="example.com")  # http=None
    assert XssScanner().scan(ctx) == []


def test_xss_failed_request_yields_no_findings() -> None:
    endpoint = "https://example.com/search?q=test"
    # No canned responses -> all requests fail -> no findings
    client = FakeHttpClient({})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )
    assert XssScanner().scan(ctx) == []


def test_xss_reflection_detected_creates_finding_with_m2_fields() -> None:
    """Marker reflected unencoded -> finding with CVSS, CWE, OWASP, remediation."""
    endpoint = "https://example.com/search?q=test"
    marker = REFLECTION_MARKERS[0]
    # Body contains the marker exactly as sent (unencoded)
    body = f"<html><body>Search results for: {marker}</body></html>"
    # The plugin builds test URL by replacing param value with marker
    test_url = endpoint.replace("test", marker)
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = XssScanner().scan(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.plugin == "xss"
    assert f.name == "Reflected XSS in parameter 'q'"
    assert f.severity is Severity.MEDIUM
    assert f.target == test_url  # final URL after redirects (none here)
    assert f.confidence is Confidence.MEDIUM
    assert marker in f.evidence
    assert "q" in f.metadata["parameter"]
    assert f.metadata["marker"] == marker

    # M2 advanced fields
    assert f.cvss is not None
    assert f.cvss.version == "3.1"
    assert f.cvss.base_score == 6.1
    assert "AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N" in f.cvss.vector
    assert f.cwe_ids == ("CWE-79",)
    assert f.owasp_categories == ("A03:2021-Injection",)
    assert f.remediation is not None
    assert "Contextually encode" in f.remediation
    assert "Content Security Policy" in f.remediation


def test_xss_no_reflection_no_finding() -> None:
    """Marker NOT reflected -> no finding."""
    endpoint = "https://example.com/search?q=test"
    marker = REFLECTION_MARKERS[0]
    # Body does NOT contain the marker
    body = "<html><body>Search results for: something_else</body></html>"
    test_url = endpoint.replace("test", marker)
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    assert XssScanner().scan(ctx) == []


def test_xss_multiple_parameters_only_vulnerable_reported() -> None:
    """Two params, only one reflects -> one finding."""
    endpoint = "https://example.com/search?q=test&page=1"
    marker = REFLECTION_MARKERS[0]
    # Only 'q' reflects
    body = f"<html><body>Results for {marker} on page 1</body></html>"
    test_url = endpoint.replace("test", marker)  # q=test -> q=marker
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = XssScanner().scan(ctx)

    assert len(findings) == 1
    assert findings[0].metadata["parameter"] == "q"


def test_xss_respects_max_endpoints_limit() -> None:
    """Only first max_endpoints endpoints are tested."""
    # Create 3 endpoints, set max_endpoints=2
    endpoints = [
        f"https://example.com/search?q=test{i}" for i in range(3)
    ]
    # All reflect the marker
    marker = REFLECTION_MARKERS[0]
    responses = {
        ep: response(ep, body=f"<html>{marker}</html>")
        for ep in endpoints
    }
    # Need canned responses for the modified URLs with markers
    for ep in endpoints:
        test_url = ep.replace("test0", marker)  # this is wrong, let me think...
    # Actually the plugin builds test URLs by replacing param values with markers
    # So we need to add those to the responses
    for ep in endpoints:
        test_url_q = ep.replace("test0", marker).replace("test1", marker).replace("test2", marker)
        # More precisely: the plugin uses with_param_value which replaces the param value
        from app.infrastructure.scanner.plugins._params import with_param_value
        test_url = with_param_value(ep, "q", marker)
        responses[test_url] = response(test_url, body=f"<html>{marker}</html>")

    client = FakeHttpClient(responses)
    cfg = ScannerConfig(max_endpoints=2)
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        config=cfg,
        endpoints=tuple(type("Endpoint", (), {"url": ep}) for ep in endpoints),
    )

    findings = XssScanner().scan(ctx)

    # Only 2 endpoints tested -> 2 findings
    assert len(findings) == 2


def test_xss_uses_both_markers_stops_after_first_hit_per_param() -> None:
    """If first marker reflects, second not tested for that param."""
    endpoint = "https://example.com/search?q=test"
    # First marker reflects
    body = f"<html><body>{REFLECTION_MARKERS[0]}</body></html>"
    # Need responses for both the original endpoint and the test URLs
    from app.infrastructure.scanner.plugins._params import with_param_value
    test_url_0 = with_param_value(endpoint, "q", REFLECTION_MARKERS[0])
    responses = {
        endpoint: response(endpoint, body=""),
        test_url_0: response(test_url_0, body=body),
    }
    client = FakeHttpClient(responses)
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = XssScanner().scan(ctx)

    assert len(findings) == 1
    # Only first marker should be in evidence
    assert REFLECTION_MARKERS[0] in findings[0].evidence
    assert REFLECTION_MARKERS[1] not in findings[0].evidence


# --- SQL Injection (error-based) ---------------------------------------------
def test_sqli_noop_without_http_client() -> None:
    ctx = ScanContext(target_domain="example.com")  # http=None
    assert SqliScanner().scan(ctx) == []


def test_sqli_failed_request_yields_no_findings() -> None:
    endpoint = "https://example.com/search?q=test"
    client = FakeHttpClient({})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )
    assert SqliScanner().scan(ctx) == []


def test_sqli_mysql_error_detected() -> None:
    """MySQL error in response -> finding with M2 fields (provisional CVSS 5.3)."""
    endpoint = "https://example.com/search?q=test"
    marker = ERROR_MARKERS[0]  # '
    test_url = with_param_value(endpoint, "q", marker)
    body = "You have an error in your SQL syntax near '' at line 1"
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.plugin == "sqli"
    assert f.name == "Potential SQL Injection in parameter 'q'"
    assert f.severity is Severity.MEDIUM
    assert f.confidence is Confidence.MEDIUM
    assert f.cvss is not None
    assert f.cvss.base_score == 5.3
    assert "AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N" in f.cvss.vector
    assert f.cwe_ids == ("CWE-89",)
    assert f.owasp_categories == ("A03:2021-Injection",)
    assert f.remediation is not None
    assert "parameterized queries" in f.remediation.lower()
    assert f.metadata["db_type"] == "mysql"


def test_sqli_postgres_error_detected() -> None:
    """PostgreSQL error in response -> finding."""
    endpoint = "https://example.com/item?id=1"
    marker = ERROR_MARKERS[0]
    test_url = with_param_value(endpoint, "id", marker)
    body = "syntax error at or near \"'\" at character 42"
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["db_type"] == "postgresql"


def test_sqli_sqlserver_error_detected() -> None:
    """SQL Server error in response -> finding."""
    endpoint = "https://example.com/item?id=1"
    marker = ERROR_MARKERS[0]
    test_url = with_param_value(endpoint, "id", marker)
    body = "Unclosed quotation mark after the character string '''."
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["db_type"] == "sqlserver"


def test_sqli_oracle_error_detected() -> None:
    """Oracle error in response -> finding."""
    endpoint = "https://example.com/item?id=1"
    marker = ERROR_MARKERS[0]
    test_url = with_param_value(endpoint, "id", marker)
    body = "ORA-00933: SQL command not properly ended"
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["db_type"] == "oracle"


def test_sqli_sqlite_error_detected() -> None:
    """SQLite error in response -> finding."""
    endpoint = "https://example.com/item?id=1"
    marker = ERROR_MARKERS[0]
    test_url = with_param_value(endpoint, "id", marker)
    body = "sqlite3.OperationalError: near \"'\": syntax error"
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["db_type"] == "sqlite"


def test_sqli_no_db_error_no_finding() -> None:
    """Generic error / no error -> no finding."""
    endpoint = "https://example.com/search?q=test"
    marker = ERROR_MARKERS[0]
    test_url = with_param_value(endpoint, "q", marker)
    body = "Internal Server Error: something went wrong"  # Not a DB error
    client = FakeHttpClient({test_url: response(test_url, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    assert SqliScanner().scan(ctx) == []


def test_sqli_respects_max_endpoints_limit() -> None:
    """Only first max_endpoints endpoints are tested."""
    endpoints = [f"https://example.com/search?q=test{i}" for i in range(3)]
    marker = ERROR_MARKERS[0]
    responses = {}
    for ep in endpoints:
        test_url = with_param_value(ep, "q", marker)
        responses[test_url] = response(test_url, body="You have an error in your SQL syntax")

    client = FakeHttpClient(responses)
    cfg = ScannerConfig(max_endpoints=2)
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        config=cfg,
        endpoints=tuple(type("Endpoint", (), {"url": ep}) for ep in endpoints),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 2


def test_sqli_multiple_parameters_only_vulnerable_reported() -> None:
    """Two params, only one triggers DB error -> one finding."""
    endpoint = "https://example.com/search?q=test&page=1"
    marker = ERROR_MARKERS[0]
    test_url_q = with_param_value(endpoint, "q", marker)
    body = "You have an error in your SQL syntax near '' at line 1"
    client = FakeHttpClient({test_url_q: response(test_url_q, body=body)})
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["parameter"] == "q"


def test_sqli_uses_all_markers_stops_after_first_hit_per_param() -> None:
    """If first marker triggers error, subsequent markers not tested for that param."""
    endpoint = "https://example.com/search?q=test"
    body = "You have an error in your SQL syntax near '' at line 1"
    # Only first marker's test URL has a response
    test_url_0 = with_param_value(endpoint, "q", ERROR_MARKERS[0])
    responses = {test_url_0: response(test_url_0, body=body)}
    client = FakeHttpClient(responses)
    ctx = ScanContext(
        target_domain="example.com",
        http=client,
        endpoints=(type("Endpoint", (), {"url": endpoint}),),
    )

    findings = SqliScanner().scan(ctx)
    assert len(findings) == 1
    assert findings[0].metadata["marker"] == ERROR_MARKERS[0]
