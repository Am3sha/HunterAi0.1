"""Shared read-only HTTP client implementation.

``UrllibHttpClient`` performs GET/HEAD using only the standard library. It:
- applies a strict default timeout (5s),
- follows redirects and records the final URL,
- captures response headers even on 4xx/5xx (we still want to inspect them),
- caps the body it reads (header inspection doesn't need large bodies).

``ScopedHttpClient`` wraps any HttpClient and refuses URLs outside the authorized
``TargetScope`` — the enforcement point for "authorized target scope only".
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from app.core.logging import get_logger
from app.domain.entities.http import HttpHeaders, HttpResponse, TargetScope
from app.domain.ports.http import HttpClient, HttpClientError, OutOfScopeError

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 5.0
_MAX_BODY_BYTES = 256 * 1024  # 256 KiB is plenty for header/body heuristics
_USER_AGENT = "HunterAI-Scanner/0.1 (authorized testing)"


class UrllibHttpClient(HttpClient):
    """Read-only HTTP client built on urllib (GET/HEAD only)."""

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        return self._request("GET", url, headers=headers, timeout=timeout)

    def head(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        return self._request("HEAD", url, headers=headers, timeout=timeout)

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None,
        timeout: float | None,
    ) -> HttpResponse:
        request_headers = {"User-Agent": _USER_AGENT, **(headers or {})}
        request = urllib.request.Request(url, method=method, headers=request_headers)
        effective_timeout = timeout if timeout is not None else self._timeout
        # Default context verifies TLS; we only READ, so verification failures are
        # surfaced as errors (a plugin may still note plaintext/redirect behaviour).
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(request, timeout=effective_timeout, context=context) as resp:
                return self._to_response(url, resp.geturl(), resp.status, resp.headers, resp, method)
        except urllib.error.HTTPError as exc:
            # 4xx/5xx still carry headers worth inspecting.
            return self._to_response(url, exc.geturl(), exc.code, exc.headers, exc, method)
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError, ValueError) as exc:
            raise HttpClientError(f"{method} {url} failed: {exc}") from exc

    @staticmethod
    def _to_response(requested_url, final_url, status, raw_headers, stream, method) -> HttpResponse:
        items = list(raw_headers.items()) if raw_headers is not None else []
        body = ""
        if method != "HEAD":
            try:
                body = stream.read(_MAX_BODY_BYTES).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - body is best-effort
                body = ""
        return HttpResponse(
            url=final_url or requested_url,
            status_code=int(status),
            headers=HttpHeaders(items),
            body=body,
            requested_url=requested_url,
        )


class ScopedHttpClient(HttpClient):
    """Wraps an HttpClient and enforces the authorized target scope."""

    def __init__(self, inner: HttpClient, scope: TargetScope) -> None:
        self._inner = inner
        self._scope = scope

    def get(self, url, *, headers=None, timeout=None) -> HttpResponse:
        self._check(url)
        return self._inner.get(url, headers=headers, timeout=timeout)

    def head(self, url, *, headers=None, timeout=None) -> HttpResponse:
        self._check(url)
        return self._inner.head(url, headers=headers, timeout=timeout)

    def _check(self, url: str) -> None:
        if not self._scope.allows_url(url):
            raise OutOfScopeError(f"URL out of authorized scope: {url}")


def build_scoped_http_client(scope: TargetScope, timeout: float = _DEFAULT_TIMEOUT) -> HttpClient:
    """Build the read-only, scope-enforcing HTTP client used during a scan."""
    return ScopedHttpClient(UrllibHttpClient(timeout=timeout), scope)
