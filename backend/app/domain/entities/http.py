"""HTTP value objects for scanner plugins.

Pure domain data. ``HttpHeaders`` is case-insensitive (HTTP header names are not
case-sensitive). ``HttpResponse`` is what the shared HTTP client returns to a
plugin; ``TargetScope`` declares which hosts a scan is authorized to touch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit


class HttpHeaders:
    """Case-insensitive, multi-value view of HTTP response headers."""

    __slots__ = ("_items",)

    def __init__(self, items: "list[tuple[str, str]] | None" = None) -> None:
        # Preserve order and duplicates (e.g. multiple Set-Cookie).
        self._items: list[tuple[str, str]] = list(items or [])

    def get(self, name: str, default: str | None = None) -> str | None:
        """First value for ``name`` (case-insensitive), or ``default``."""
        lname = name.lower()
        for key, value in self._items:
            if key.lower() == lname:
                return value
        return default

    def get_all(self, name: str) -> list[str]:
        """All values for ``name`` (case-insensitive)."""
        lname = name.lower()
        return [value for key, value in self._items if key.lower() == lname]

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def items(self) -> list[tuple[str, str]]:
        return list(self._items)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self.has(name)


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A read-only HTTP response handed to plugins."""

    url: str
    """Final URL after any redirects."""
    status_code: int
    headers: HttpHeaders
    body: str = ""
    requested_url: str | None = None
    """The URL originally requested (differs from ``url`` if redirected)."""
    elapsed_ms: float = 0.0
    """Approximate wall-clock time for the request, in milliseconds. Populated by
    the HTTP client; intended for future time-based heuristics. 0.0 if unmeasured."""

    @property
    def redirected(self) -> bool:
        return self.requested_url is not None and self.requested_url != self.url

    @property
    def is_https(self) -> bool:
        return self.url.lower().startswith("https://")


@dataclass(frozen=True, slots=True)
class TargetScope:
    """Hosts a scan is authorized to contact.

    A request is in scope if its host equals an authorized host or is a subdomain
    of one. Built from the scan target's domain (apex + its subdomains).
    """

    hosts: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_hosts(cls, hosts: "list[str] | set[str]") -> "TargetScope":
        return cls(frozenset(h.strip().lower().rstrip(".") for h in hosts if h.strip()))

    def allows_host(self, host: str) -> bool:
        host = host.strip().lower().rstrip(".")
        if not host:
            return False
        for allowed in self.hosts:
            if host == allowed or host.endswith("." + allowed):
                return True
        return False

    def allows_url(self, url: str) -> bool:
        host = urlsplit(url).hostname or ""
        return self.allows_host(host)
