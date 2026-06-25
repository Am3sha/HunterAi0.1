"""Shared helpers for live-request scanner plugins.

Keeps each plugin file focused on its *detection logic* while centralising the
boilerplate every live plugin needs:
- a bounded number of services per run (avoid hammering a target),
- per-service error isolation (a single failed request never raises out of a
  plugin; the engine already isolates whole-plugin failures, but we also don't
  want one bad host to drop a plugin's other findings),
- a tight default timeout.

Plugins remain independent: this is a small utility, not a base class hierarchy.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from app.core.logging import get_logger
from app.domain.entities.http import HttpResponse
from app.domain.entities.recon import HttpService
from app.domain.ports.http import HttpClient, HttpClientError

logger = get_logger(__name__)

# Sensible Milestone-3 bounds (read-only header inspection).
MAX_SERVICES_PER_PLUGIN = 25
REQUEST_TIMEOUT = 5.0


def limited_services(
    services: Iterable[HttpService], limit: int = MAX_SERVICES_PER_PLUGIN
) -> list[HttpService]:
    """Return at most ``limit`` services (stable order)."""
    out: list[HttpService] = []
    for service in services:
        out.append(service)
        if len(out) >= limit:
            break
    return out


def safe_get(
    http: HttpClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> HttpResponse | None:
    """GET ``url`` (read-only), returning None on any request failure/out-of-scope."""
    try:
        return http.get(url, headers=headers, timeout=timeout)
    except HttpClientError as exc:
        logger.debug("request skipped: %s", exc)
        return None


def for_each_service_response(
    http: HttpClient,
    services: Iterable[HttpService],
    handle: Callable[[HttpService, HttpResponse], None],
    *,
    limit: int = MAX_SERVICES_PER_PLUGIN,
    headers: dict[str, str] | None = None,
) -> None:
    """GET each service URL and invoke ``handle`` with successful responses only."""
    for service in limited_services(services, limit):
        response = safe_get(http, service.url, headers=headers)
        if response is not None:
            handle(service, response)


def iter_set_cookie(response: HttpResponse) -> Iterator[str]:
    """Yield each raw Set-Cookie header value from a response."""
    yield from response.headers.get_all("set-cookie")
