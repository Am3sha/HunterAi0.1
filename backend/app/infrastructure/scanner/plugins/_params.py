"""Payload-free URL / query-parameter utilities for scanner plugins.

Generic helpers for working with URLs and their query parameters. **No
vulnerability detection logic and no payloads live here** — these only parse and
rebuild URLs. Future plugins (e.g. param-based checks) will build on top of these.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def query_params(url: str) -> list[tuple[str, str]]:
    """Return the (name, value) query parameters of ``url`` (order preserved)."""
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)


def param_names(url: str) -> list[str]:
    """Return the distinct query-parameter names of ``url`` (first-seen order)."""
    seen: list[str] = []
    for name, _ in query_params(url):
        if name not in seen:
            seen.append(name)
    return seen


def has_query_params(url: str) -> bool:
    return bool(query_params(url))


def with_param_value(url: str, name: str, value: str) -> str:
    """Return ``url`` with query parameter ``name`` set to ``value``.

    Only the first occurrence of ``name`` is replaced; other parameters and the
    rest of the URL are preserved. If ``name`` is absent, the URL is unchanged.
    Purely mechanical string manipulation — the caller decides what ``value`` is.
    """
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    replaced = False
    rebuilt: list[tuple[str, str]] = []
    for key, existing in pairs:
        if key == name and not replaced:
            rebuilt.append((key, value))
            replaced = True
        else:
            rebuilt.append((key, existing))
    if not replaced:
        return url
    new_query = urlencode(rebuilt)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def base_url(url: str) -> str:
    """Return ``url`` without its query string or fragment."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
