"""Pure parsers: raw tool output (stdout) → domain result objects.

Kept free of any subprocess/I/O so they are trivially unit-testable. Each parser
is tolerant of blank lines and malformed entries (recon tools occasionally emit
banner/log noise even in silent/JSON modes).
"""

from __future__ import annotations

import json

from app.core.logging import get_logger
from app.domain.entities.recon import Endpoint, HttpService, Subdomain

logger = get_logger(__name__)


def parse_subfinder_output(stdout: str) -> list[Subdomain]:
    """Subfinder ``-silent`` emits one hostname per line."""
    seen: set[str] = set()
    results: list[Subdomain] = []
    for line in stdout.splitlines():
        host = line.strip().lower()
        if not host or host in seen:
            continue
        seen.add(host)
        results.append(Subdomain(host=host, source="subfinder"))
    return results


def parse_httpx_output(stdout: str) -> list[HttpService]:
    """httpx ``-json`` emits one JSON object per line."""
    results: list[HttpService] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON httpx line: %.80s", line)
            continue
        url = obj.get("url")
        if not url:
            # httpx only emits a record for a live host, always with "url".
            continue
        tech = obj.get("tech") or obj.get("technologies") or []
        if isinstance(tech, str):
            tech = [tech]
        results.append(
            HttpService(
                url=url,
                input=obj.get("input"),
                status_code=_as_int(obj.get("status_code") or obj.get("status-code")),
                title=obj.get("title"),
                webserver=obj.get("webserver") or obj.get("web-server"),
                content_length=_as_int(obj.get("content_length") or obj.get("content-length")),
                host=obj.get("host"),
                technologies=tuple(str(t) for t in tech),
            )
        )
    return results


def parse_katana_output(stdout: str) -> list[Endpoint]:
    """Katana ``-jsonl`` emits one JSON object per line; bare URLs are tolerated."""
    seen: set[str] = set()
    results: list[Endpoint] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        url, method = _parse_katana_line(line)
        if not url or url in seen:
            continue
        seen.add(url)
        results.append(Endpoint(url=url, method=method, source="katana"))
    return results


def _parse_katana_line(line: str) -> tuple[str | None, str | None]:
    if not line.startswith("{"):
        return line, None  # plain URL output
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        logger.debug("Skipping non-JSON katana line: %.80s", line)
        return None, None
    request = obj.get("request") if isinstance(obj.get("request"), dict) else {}
    url = request.get("endpoint") or obj.get("endpoint") or obj.get("url")
    method = request.get("method") or obj.get("method")
    return url, method


def _as_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
