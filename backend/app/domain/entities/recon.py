"""Recon result value objects.

These are the typed outputs of each recon stage. Pure data — parsing of raw tool
output into these objects happens in the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Subdomain:
    """A discovered subdomain (Subfinder)."""

    host: str
    source: str | None = None


@dataclass(frozen=True, slots=True)
class HttpService:
    """A live HTTP service discovered while probing hosts (httpx)."""

    url: str
    input: str | None = None
    status_code: int | None = None
    title: str | None = None
    webserver: str | None = None
    content_length: int | None = None
    host: str | None = None
    technologies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Endpoint:
    """An endpoint/URL discovered while crawling (Katana)."""

    url: str
    method: str | None = None
    source: str | None = None
