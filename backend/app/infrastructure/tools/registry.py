"""Tool Registry — the declarative catalog of supported tools.

This is the **single place** to add or pin a tool. The rest of the application
discovers tools through this registry, so onboarding Nuclei / ffuf / Naabu later
is one entry here (plus, if needed, an output parser in the recon layer).

Versions are pinned for reproducibility. Integrity is verified on download:
- if a ``sha256`` is pinned on the source, it is enforced strictly;
- otherwise the asset is verified against the release's official checksums file,
  and ``setup`` prints the observed hash so you can pin it here.

To bump a tool: change the version constant below and re-run ``setup --force``.
"""

from __future__ import annotations

from app.infrastructure.tools.errors import ToolNotInRegistryError
from app.infrastructure.tools.models import BinarySource, ToolSpec

# --- Pinned versions (bump here, in one place) ---------------------------------
# Prefer the latest stable ProjectDiscovery releases; pinned for reproducibility.
SUBFINDER_VERSION = "2.14.0"
HTTPX_VERSION = "1.9.0"
KATANA_VERSION = "1.6.1"

# ProjectDiscovery publishes one .zip per OS/arch plus a *_checksums.txt per
# release. We support linux on amd64 and arm64 (Sprint 0 is Linux-first).
_PD_PLATFORMS = ("linux/amd64", "linux/arm64")


def _pd_sources(repo: str, name: str, version: str) -> dict[str, BinarySource]:
    """Build per-platform sources for a ProjectDiscovery release."""
    base = f"https://github.com/projectdiscovery/{repo}/releases/download/v{version}"
    checksums_url = f"{base}/{name}_{version}_checksums.txt"
    sources: dict[str, BinarySource] = {}
    for plat in _PD_PLATFORMS:
        arch = plat.split("/", 1)[1]
        asset = f"{name}_{version}_linux_{arch}.zip"
        sources[plat] = BinarySource(
            url=f"{base}/{asset}",
            archive_format="zip",
            archive_member=name,
            sha256=None,  # pin after first install (setup prints the hash)
            checksums_url=checksums_url,
        )
    return sources


_SPECS: dict[str, ToolSpec] = {
    "subfinder": ToolSpec(
        name="subfinder",
        version=SUBFINDER_VERSION,
        description="Passive subdomain enumeration.",
        sources=_pd_sources("subfinder", "subfinder", SUBFINDER_VERSION),
    ),
    "httpx": ToolSpec(
        name="httpx",
        version=HTTPX_VERSION,
        description="Fast HTTP probing / live-host detection.",
        sources=_pd_sources("httpx", "httpx", HTTPX_VERSION),
    ),
    "katana": ToolSpec(
        name="katana",
        version=KATANA_VERSION,
        description="Web crawling and endpoint discovery.",
        sources=_pd_sources("katana", "katana", KATANA_VERSION),
    ),
}


class ToolRegistry:
    """Read-only catalog of known tools."""

    def __init__(self, specs: dict[str, ToolSpec] | None = None) -> None:
        self._specs = specs if specs is not None else dict(_SPECS)

    def get(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise ToolNotInRegistryError(
                f"Tool '{name}' is not in the registry. Known: {', '.join(self.names())}"
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._specs

    def names(self) -> list[str]:
        return sorted(self._specs)

    def all(self) -> list[ToolSpec]:
        return [self._specs[name] for name in self.names()]
