"""Port for the shared HTTP client used by scanner plugins.

A single client is injected into the scan context and shared by all plugins (one
client, not one per plugin). It is **read-only**: only GET and HEAD are exposed.
Implementations enforce the authorized target scope and strict timeouts.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.http import HttpResponse


class HttpClientError(Exception):
    """Raised when a request fails (network error, timeout, or out of scope)."""


class OutOfScopeError(HttpClientError):
    """The requested URL is outside the authorized target scope."""


class HttpClient(Protocol):
    """Read-only HTTP client. Only safe, non-mutating methods are exposed."""

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Perform a GET request. Raises HttpClientError on failure."""
        ...

    def head(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Perform a HEAD request. Raises HttpClientError on failure."""
        ...
