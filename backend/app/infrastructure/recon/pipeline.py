"""Tool adapters implementing the recon stage ports.

Each adapter:
- builds the right CLI arguments for its tool,
- runs it through the ToolManager (which ensures it is installed),
- parses stdout into domain objects.

Tool-specific timeouts are generous defaults for Sprint 0; they can move to
configuration later.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.core.logging import get_logger
from app.domain.entities.recon import Endpoint, HttpService, Subdomain
from app.domain.ports.recon import EndpointCrawler, HttpProber, SubdomainEnumerator
from app.domain.ports.tools import ToolManagerPort
from app.infrastructure.recon.parsers import (
    parse_httpx_output,
    parse_katana_output,
    parse_subfinder_output,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class ReconLimits:
    """Per-stage timeouts (seconds) and crawl bounds."""

    subfinder_timeout: float = 180.0
    httpx_timeout: float = 240.0
    katana_timeout: float = 300.0
    katana_depth: int = 2
    katana_max_targets: int = 50


class SubfinderEnumerator(SubdomainEnumerator):
    def __init__(self, tools: ToolManagerPort, limits: ReconLimits | None = None) -> None:
        self._tools = tools
        self._limits = limits or ReconLimits()

    def enumerate(self, domain: str) -> list[Subdomain]:
        result = self._tools.run(
            "subfinder",
            ["-d", domain, "-silent"],
            timeout=self._limits.subfinder_timeout,
        )
        if not result.ok:
            logger.warning("subfinder exited %d: %.200s", result.returncode, result.stderr)
        return parse_subfinder_output(result.stdout)


class HttpxProber(HttpProber):
    def __init__(self, tools: ToolManagerPort, limits: ReconLimits | None = None) -> None:
        self._tools = tools
        self._limits = limits or ReconLimits()

    def probe(self, hosts: Sequence[str]) -> list[HttpService]:
        if not hosts:
            return []
        args = [
            "-json",
            "-silent",
            "-no-color",
            "-title",
            "-status-code",
            "-web-server",
            "-tech-detect",
            "-follow-redirects",
        ]
        result = self._tools.run(
            "httpx",
            args,
            timeout=self._limits.httpx_timeout,
            input_text="\n".join(hosts) + "\n",
        )
        if not result.ok:
            logger.warning("httpx exited %d: %.200s", result.returncode, result.stderr)
        return parse_httpx_output(result.stdout)


class KatanaCrawler(EndpointCrawler):
    def __init__(self, tools: ToolManagerPort, limits: ReconLimits | None = None) -> None:
        self._tools = tools
        self._limits = limits or ReconLimits()

    def crawl(self, urls: Sequence[str]) -> list[Endpoint]:
        if not urls:
            return []
        targets = list(urls)[: self._limits.katana_max_targets]
        if len(urls) > len(targets):
            logger.info(
                "Crawling first %d of %d URLs (katana_max_targets)", len(targets), len(urls)
            )
        args = [
            "-jsonl",
            "-silent",
            "-no-color",
            "-depth",
            str(self._limits.katana_depth),
        ]
        result = self._tools.run(
            "katana",
            args,
            timeout=self._limits.katana_timeout,
            input_text="\n".join(targets) + "\n",
        )
        if not result.ok:
            logger.warning("katana exited %d: %.200s", result.returncode, result.stderr)
        return parse_katana_output(result.stdout)


def build_recon_pipeline(
    tools: ToolManagerPort, limits: ReconLimits | None = None
) -> tuple[SubfinderEnumerator, HttpxProber, KatanaCrawler]:
    """Assemble the three recon stage adapters over a shared ToolManager."""
    limits = limits or ReconLimits()
    return (
        SubfinderEnumerator(tools, limits),
        HttpxProber(tools, limits),
        KatanaCrawler(tools, limits),
    )
