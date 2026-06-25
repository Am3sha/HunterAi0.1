"""Tool Manager — orchestrates discovery, installation, status, and execution.

This is the public face of the subsystem and the concrete implementation behind
``ToolManagerPort``. It ties together:
- ``ToolRegistry``  (what tools exist, pinned versions, sources)
- ``ToolProvider``  (how to acquire + verify a binary)
- ``ToolExecutor``  (how to run a binary)

On-disk layout (under the managed tools dir)::

    <tools_dir>/<name>/<name>          # the executable
    <tools_dir>/<name>/.meta.json      # {name, version, sha256, source_url, installed_at}

Installs are idempotent: a tool already present at the pinned version is skipped
unless ``force=True``.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger
from app.domain.entities.tool import ToolExecutionResult
from app.infrastructure.tools.errors import (
    ToolNotInstalledError,
    UnsupportedPlatformError,
)
from app.infrastructure.tools.executor import ToolExecutor
from app.infrastructure.tools.models import (
    InstalledTool,
    ToolSpec,
    ToolStatus,
    current_platform,
)
from app.infrastructure.tools.provider import GitHubReleaseProvider, ToolProvider
from app.infrastructure.tools.registry import ToolRegistry

logger = get_logger(__name__)

_META_FILENAME = ".meta.json"


class ToolManager:
    """Orchestrates the tool lifecycle and runs managed tools by name."""

    def __init__(
        self,
        tools_dir: Path,
        registry: ToolRegistry | None = None,
        provider: ToolProvider | None = None,
        executor: ToolExecutor | None = None,
        platform_key: str | None = None,
    ) -> None:
        self._tools_dir = Path(tools_dir)
        self._registry = registry or ToolRegistry()
        self._provider = provider or GitHubReleaseProvider()
        self._executor = executor or ToolExecutor()
        self._platform = platform_key or current_platform()

    @property
    def tools_dir(self) -> Path:
        return self._tools_dir

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    # -- discovery / status ---------------------------------------------------
    def status(self) -> list[ToolStatus]:
        """Report required vs. installed state for every registered tool."""
        return [self._status_for(spec) for spec in self._registry.all()]

    def _status_for(self, spec: ToolSpec) -> ToolStatus:
        meta = self._read_meta(spec.name)
        binary = self._binary_path(spec.name)
        installed = meta is not None and binary.exists()
        return ToolStatus(
            name=spec.name,
            required_version=spec.version,
            installed=installed,
            installed_version=meta.get("version") if meta else None,
            path=binary if installed else None,
        )

    def is_installed(self, name: str) -> bool:
        spec = self._registry.get(name)
        meta = self._read_meta(name)
        return (
            meta is not None
            and meta.get("version") == spec.version
            and self._binary_path(name).exists()
        )

    # -- installation ---------------------------------------------------------
    def install(self, name: str, *, force: bool = False) -> InstalledTool:
        """Install a single tool at its pinned version (idempotent)."""
        spec = self._registry.get(name)

        if not force and self.is_installed(name):
            logger.info("%s v%s already installed — skipping", spec.name, spec.version)
            return self._installed_from_meta(spec)

        source = spec.source_for(self._platform)
        if source is None:
            raise UnsupportedPlatformError(
                f"No source for '{name}' on platform '{self._platform}'. "
                f"Available: {', '.join(spec.sources) or 'none'}"
            )

        dest_dir = self._tools_dir / name
        installed = self._provider.install(spec, source, dest_dir)
        self._write_meta(installed, source_url=source.url)
        return installed

    def install_all(self, *, force: bool = False) -> list[InstalledTool]:
        """Install every registered tool (used by ``setup``)."""
        return [self.install(name, force=force) for name in self._registry.names()]

    def update(self, name: str) -> InstalledTool:
        """Ensure the pinned version is present (re-installs if version differs)."""
        return self.install(name, force=not self.is_installed(name))

    # -- resolution / execution ----------------------------------------------
    def resolve_path(self, name: str) -> Path:
        spec = self._registry.get(name)
        binary = self._binary_path(spec.name)
        if not binary.exists():
            raise ToolNotInstalledError(
                f"'{name}' is not installed. Run setup to install it."
            )
        return binary

    def ensure_installed(self, name: str) -> Path:
        if not self.is_installed(name):
            self.install(name)
        return self.resolve_path(name)

    def run(
        self,
        name: str,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        input_text: str | None = None,
    ) -> ToolExecutionResult:
        executable = self.ensure_installed(name)
        return self._executor.run(
            executable, args, timeout=timeout, input_text=input_text
        )

    # -- metadata helpers -----------------------------------------------------
    def _binary_path(self, name: str) -> Path:
        return self._tools_dir / name / name

    def _meta_path(self, name: str) -> Path:
        return self._tools_dir / name / _META_FILENAME

    def _read_meta(self, name: str) -> dict | None:
        meta_path = self._meta_path(name)
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt metadata for %s at %s", name, meta_path)
            return None

    def _write_meta(self, installed: InstalledTool, *, source_url: str) -> None:
        meta = {
            "name": installed.name,
            "version": installed.version,
            "sha256": installed.sha256,
            "source_url": source_url,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._meta_path(installed.name).write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    def _installed_from_meta(self, spec: ToolSpec) -> InstalledTool:
        meta = self._read_meta(spec.name) or {}
        return InstalledTool(
            name=spec.name,
            version=meta.get("version", spec.version),
            path=self._binary_path(spec.name),
            sha256=meta.get("sha256", ""),
        )
