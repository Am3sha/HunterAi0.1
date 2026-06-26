"""Tests for Sprint 2 M1 infrastructure additions (additive seams).

Covers: HttpResponse.elapsed_ms default, ScannerConfig defaults, ScanContext
tools/config injection + parameterized_endpoints(), and the payload-free param
utilities. No plugin behaviour is exercised here.
"""

from __future__ import annotations

from app.domain.entities.http import HttpHeaders, HttpResponse
from app.domain.entities.recon import Endpoint, HttpService
from app.domain.entities.scan import Scan
from app.domain.entities.scanner import ScanContext
from app.domain.entities.scanner_config import (
    DEFAULT_MAX_ENDPOINTS,
    DEFAULT_MAX_SERVICES,
    DEFAULT_REQUEST_TIMEOUT,
    ScannerConfig,
)
from app.infrastructure.scanner.plugins import _params
from uuid import uuid4


# --- HttpResponse.elapsed_ms -------------------------------------------------
def test_http_response_elapsed_ms_defaults_to_zero() -> None:
    resp = HttpResponse(url="https://example.com", status_code=200, headers=HttpHeaders())
    assert resp.elapsed_ms == 0.0


def test_http_response_elapsed_ms_is_settable() -> None:
    resp = HttpResponse(
        url="https://example.com", status_code=200, headers=HttpHeaders(), elapsed_ms=12.5
    )
    assert resp.elapsed_ms == 12.5


# --- ScannerConfig -----------------------------------------------------------
def test_scanner_config_defaults_match_historical_constants() -> None:
    config = ScannerConfig()
    assert config.request_timeout == DEFAULT_REQUEST_TIMEOUT == 5.0
    assert config.max_services == DEFAULT_MAX_SERVICES == 25
    assert config.max_endpoints == DEFAULT_MAX_ENDPOINTS == 50


def test_scanner_config_is_overridable() -> None:
    config = ScannerConfig(request_timeout=3.0, max_services=10, max_endpoints=20)
    assert (config.request_timeout, config.max_services, config.max_endpoints) == (3.0, 10, 20)


# --- ScanContext additions ---------------------------------------------------
def test_scancontext_defaults_keep_capabilities_optional() -> None:
    ctx = ScanContext(target_domain="example.com")
    assert ctx.http is None
    assert ctx.tools is None
    assert isinstance(ctx.config, ScannerConfig)  # default applied
    assert ctx.config.max_services == DEFAULT_MAX_SERVICES


def test_scancontext_carries_injected_tools_and_config() -> None:
    sentinel_tools = object()
    cfg = ScannerConfig(max_services=3)
    ctx = ScanContext(target_domain="example.com", tools=sentinel_tools, config=cfg)
    assert ctx.tools is sentinel_tools
    assert ctx.config.max_services == 3


def test_parameterized_endpoints_filters_to_querystring_urls() -> None:
    ctx = ScanContext(
        target_domain="example.com",
        endpoints=(
            Endpoint(url="https://example.com/search?q=1"),
            Endpoint(url="https://example.com/about"),
            Endpoint(url="https://example.com/x?"),  # empty query -> excluded
        ),
    )
    urls = [e.url for e in ctx.parameterized_endpoints()]
    assert urls == ["https://example.com/search?q=1"]


def test_from_scan_passes_through_tools_and_config() -> None:
    scan = Scan.create(uuid4(), "example.com")
    scan.services = [HttpService(url="https://example.com")]
    sentinel_tools = object()
    cfg = ScannerConfig(max_endpoints=7)
    ctx = ScanContext.from_scan(scan, http=None, tools=sentinel_tools, config=cfg)
    assert ctx.tools is sentinel_tools
    assert ctx.config.max_endpoints == 7
    assert ctx.service_urls == ["https://example.com"]


def test_from_scan_applies_default_config_when_omitted() -> None:
    scan = Scan.create(uuid4(), "example.com")
    ctx = ScanContext.from_scan(scan)
    assert isinstance(ctx.config, ScannerConfig)
    assert ctx.tools is None


# --- param utilities (payload-free) ------------------------------------------
def test_query_params_and_names() -> None:
    url = "https://example.com/s?q=hello&page=2&q=again"
    assert _params.query_params(url) == [("q", "hello"), ("page", "2"), ("q", "again")]
    assert _params.param_names(url) == ["q", "page"]
    assert _params.has_query_params(url)
    assert not _params.has_query_params("https://example.com/s")


def test_with_param_value_replaces_first_occurrence_only() -> None:
    url = "https://example.com/s?q=a&page=2"
    out = _params.with_param_value(url, "q", "REPLACED")
    assert "q=REPLACED" in out
    assert "page=2" in out


def test_with_param_value_noop_when_param_absent() -> None:
    url = "https://example.com/s?q=a"
    assert _params.with_param_value(url, "missing", "x") == url


def test_base_url_strips_query_and_fragment() -> None:
    assert _params.base_url("https://example.com/p?a=1#frag") == "https://example.com/p"
