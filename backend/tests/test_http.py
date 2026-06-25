"""Tests for the shared HTTP value objects and the scope-enforcing client."""

from __future__ import annotations

import pytest

from app.domain.entities.http import HttpHeaders, HttpResponse, TargetScope
from app.domain.ports.http import HttpClient, OutOfScopeError
from app.infrastructure.http import ScopedHttpClient


def test_headers_case_insensitive_and_multivalue() -> None:
    headers = HttpHeaders(
        [("Content-Type", "text/html"), ("Set-Cookie", "a=1"), ("set-cookie", "b=2")]
    )
    assert headers.get("content-type") == "text/html"
    assert headers.get("CONTENT-TYPE") == "text/html"
    assert headers.has("Set-Cookie")
    assert headers.get_all("set-cookie") == ["a=1", "b=2"]
    assert headers.get("missing") is None


def test_target_scope_allows_apex_and_subdomains_only() -> None:
    scope = TargetScope.from_hosts({"example.com"})
    assert scope.allows_url("https://example.com/")
    assert scope.allows_url("https://api.example.com/v1")
    assert scope.allows_url("http://EXAMPLE.COM")
    assert not scope.allows_url("https://evil.com/")
    assert not scope.allows_url("https://notexample.com/")
    assert not scope.allows_url("https://example.com.evil.com/")


class _RecordingClient(HttpClient):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, url, *, headers=None, timeout=None) -> HttpResponse:
        self.calls.append(url)
        return HttpResponse(url=url, status_code=200, headers=HttpHeaders())

    def head(self, url, *, headers=None, timeout=None) -> HttpResponse:
        self.calls.append(url)
        return HttpResponse(url=url, status_code=200, headers=HttpHeaders())


def test_scoped_client_blocks_out_of_scope() -> None:
    inner = _RecordingClient()
    client = ScopedHttpClient(inner, TargetScope.from_hosts({"example.com"}))

    assert client.get("https://api.example.com/").status_code == 200
    with pytest.raises(OutOfScopeError):
        client.get("https://evil.com/")
    # The blocked request never reached the inner client.
    assert inner.calls == ["https://api.example.com/"]
