"""Ports for the reconnaissance pipeline.

Each stage is a single-method Protocol so it can be implemented by a tool adapter
today (Subfinder/httpx/Katana) and swapped or extended later (e.g. an alternative
enumerator, or an AI-assisted crawler) without touching the use case.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.entities.recon import Endpoint, HttpService, Subdomain


class SubdomainEnumerator(Protocol):
    """Discovers subdomains for a root domain."""

    def enumerate(self, domain: str) -> list[Subdomain]: ...


class HttpProber(Protocol):
    """Probes hosts and returns the ones serving live HTTP(S) services."""

    def probe(self, hosts: Sequence[str]) -> list[HttpService]: ...


class EndpointCrawler(Protocol):
    """Crawls live URLs and returns discovered endpoints."""

    def crawl(self, urls: Sequence[str]) -> list[Endpoint]: ...
