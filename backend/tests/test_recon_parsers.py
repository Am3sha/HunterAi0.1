"""Tests for recon output parsers (pure, no I/O)."""

from __future__ import annotations

from app.infrastructure.recon.parsers import (
    parse_httpx_output,
    parse_katana_output,
    parse_subfinder_output,
)


def test_parse_subfinder_dedupes_and_lowercases() -> None:
    out = "api.example.com\nAPI.example.com\n\n  www.example.com  \n"
    subs = parse_subfinder_output(out)
    assert [s.host for s in subs] == ["api.example.com", "www.example.com"]
    assert all(s.source == "subfinder" for s in subs)


def test_parse_httpx_extracts_fields_and_skips_noise() -> None:
    out = "\n".join(
        [
            "not-json-banner-line",
            '{"url":"https://www.example.com","input":"www.example.com",'
            '"status_code":200,"title":"Example","webserver":"nginx",'
            '"content_length":1256,"host":"93.184.216.34","tech":["Nginx","HSTS"]}',
            '{"input":"dead.example.com"}',  # no url -> skipped
        ]
    )
    services = parse_httpx_output(out)
    assert len(services) == 1
    svc = services[0]
    assert svc.url == "https://www.example.com"
    assert svc.status_code == 200
    assert svc.title == "Example"
    assert svc.webserver == "nginx"
    assert svc.content_length == 1256
    assert svc.technologies == ("Nginx", "HSTS")


def test_parse_httpx_handles_hyphenated_keys() -> None:
    out = '{"url":"https://x.example.com","status-code":403,"web-server":"Apache"}'
    services = parse_httpx_output(out)
    assert services[0].status_code == 403
    assert services[0].webserver == "Apache"


def test_parse_katana_jsonl_and_bare_urls() -> None:
    out = "\n".join(
        [
            '{"request":{"method":"GET","endpoint":"https://example.com/login"}}',
            "https://example.com/about",
            '{"request":{"method":"GET","endpoint":"https://example.com/login"}}',  # dup
            "garbage {not json",
        ]
    )
    endpoints = parse_katana_output(out)
    urls = [e.url for e in endpoints]
    assert urls == ["https://example.com/login", "https://example.com/about", "garbage {not json"]
    assert endpoints[0].method == "GET"
    assert all(e.source == "katana" for e in endpoints)
