"""Target entity — a thing we are authorized to test.

In Sprint 0 a target is a root domain (e.g. ``example.com``). The value is
normalised on creation so the rest of the system works with a canonical form.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))+$"
)


def normalize_domain(raw: str) -> str:
    """Canonicalise a user-supplied domain.

    Strips scheme, path, port, whitespace and a trailing dot; lowercases.
    Raises ``ValueError`` if the result is not a valid domain name.
    """
    value = raw.strip().lower()
    if not value:
        raise ValueError("Target domain must not be empty")
    value = _SCHEME_RE.sub("", value)  # drop http:// etc.
    value = value.split("/", 1)[0]  # drop any path
    value = value.split(":", 1)[0]  # drop any port
    value = value.rstrip(".")
    if not _DOMAIN_RE.match(value):
        raise ValueError(f"Invalid target domain: {raw!r}")
    return value


@dataclass(frozen=True, slots=True)
class Target:
    """A root domain authorized for testing."""

    id: UUID
    domain: str
    created_at: datetime

    @classmethod
    def create(cls, raw_domain: str, *, now: datetime | None = None) -> "Target":
        return cls(
            id=uuid4(),
            domain=normalize_domain(raw_domain),
            created_at=now or datetime.now(timezone.utc),
        )
