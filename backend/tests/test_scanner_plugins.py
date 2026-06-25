"""Tests for the five Milestone-3 scanner plugins."""

from __future__ import annotations

from app.domain.entities.finding import Severity
from app.domain.entities.scanner import ScanContext
from app.infrastructure.scanner.plugins.clickjacking import ClickjackingScanner
from app.infrastructure.scanner.plugins.cookie_security import CookieSecurityScanner
from app.infrastructure.scanner.plugins.cors import CorsScanner, _PROBE_ORIGIN
from app.infrastructure.scanner.plugins.security_headers import SecurityHeadersScanner
from app.infrastructure.scanner.plugins.tls_hygiene import TlsHygieneScanner
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
    ):
        assert plugin.scan(ctx) == []


def test_failed_request_yields_no_findings_not_an_exception() -> None:
    # Empty canned map => every request raises HttpClientError internally.
    client = FakeHttpClient({})
    ctx = context_for([URL], client)
    # Must not raise; just produces nothing.
    assert SecurityHeadersScanner().scan(ctx) == []


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
