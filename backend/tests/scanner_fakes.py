"""Shared test helper: a fake HttpClient returning canned responses by URL."""

from __future__ import annotations

from app.domain.entities.http import HttpHeaders, HttpResponse
from app.domain.entities.recon import HttpService
from app.domain.entities.scanner import ScanContext
from app.domain.ports.http import HttpClient, HttpClientError


class FakeHttpClient(HttpClient):
    """Returns a pre-seeded HttpResponse per URL; raises if a URL is unknown."""

    def __init__(self, responses: dict[str, HttpResponse]) -> None:
        self._responses = responses
        self.requested: list[str] = []

    def get(self, url, *, headers=None, timeout=None) -> HttpResponse:
        self.requested.append(url)
        if url not in self._responses:
            raise HttpClientError(f"no canned response for {url}")
        return self._responses[url]

    def head(self, url, *, headers=None, timeout=None) -> HttpResponse:
        return self.get(url, headers=headers, timeout=timeout)


def response(
    url: str,
    *,
    status: int = 200,
    headers: list[tuple[str, str]] | None = None,
    body: str = "",
    requested_url: str | None = None,
) -> HttpResponse:
    return HttpResponse(
        url=url,
        status_code=status,
        headers=HttpHeaders(headers or []),
        body=body,
        requested_url=requested_url,
    )


def context_for(urls: list[str], client: HttpClient) -> ScanContext:
    return ScanContext(
        target_domain="example.com",
        services=tuple(HttpService(url=u, status_code=200) for u in urls),
        http=client,
    )
