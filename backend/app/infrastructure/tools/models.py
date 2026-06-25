"""Data models for the Tool Management subsystem.

These describe *how a tool is acquired and what is installed*. They are
infrastructure concerns (not domain entities): the catalog of download URLs,
checksums, and on-disk install metadata.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ArchiveFormat = Literal["zip", "tar.gz", "raw"]


def current_platform() -> str:
    """Return a ``"<os>/<arch>"`` key, normalised to match registry source keys.

    Examples: ``"linux/amd64"``, ``"linux/arm64"``. On unsupported hosts this
    still returns a best-effort key (e.g. ``"windows/amd64"``) so callers can
    surface a clear UnsupportedPlatformError rather than crashing.
    """
    os_name = platform.system().lower()
    machine = platform.machine().lower()
    arch = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine, machine)
    return f"{os_name}/{arch}"


@dataclass(frozen=True, slots=True)
class BinarySource:
    """Where and how to obtain a tool binary for one platform."""

    url: str
    archive_format: ArchiveFormat
    archive_member: str
    """Name of the binary inside the archive (``"raw"`` => the download itself)."""
    sha256: str | None = None
    """Pinned SHA-256 of the downloaded asset. When set, it is strictly enforced."""
    checksums_url: str | None = None
    """Official checksums file used to verify the asset when ``sha256`` is unset."""

    @property
    def asset_filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A registry entry: one tool pinned to one version, per platform."""

    name: str
    version: str
    description: str
    sources: dict[str, BinarySource]
    version_args: tuple[str, ...] = ("-version",)

    def source_for(self, platform_key: str) -> BinarySource | None:
        return self.sources.get(platform_key)


@dataclass(frozen=True, slots=True)
class InstalledTool:
    """A tool present in the managed tools directory."""

    name: str
    version: str
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class ToolStatus:
    """Discovery view: required vs. installed state for a tool."""

    name: str
    required_version: str
    installed: bool
    installed_version: str | None = None
    path: Path | None = None

    @property
    def needs_install(self) -> bool:
        return not self.installed or self.installed_version != self.required_version
