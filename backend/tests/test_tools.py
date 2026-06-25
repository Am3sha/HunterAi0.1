"""Tests for the Tool Management subsystem (no network required)."""

from __future__ import annotations

import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pytest

from app.domain.entities.tool import ToolExecutionResult
from app.infrastructure.tools import ToolExecutor, ToolManager, ToolRegistry
from app.infrastructure.tools.errors import (
    ChecksumMismatchError,
    ToolNotInRegistryError,
    ToolNotInstalledError,
)
from app.infrastructure.tools.models import BinarySource, InstalledTool, ToolSpec
from app.infrastructure.tools.provider import ToolProvider


# --- Registry ----------------------------------------------------------------
def test_registry_contains_sprint0_tools() -> None:
    registry = ToolRegistry()
    assert registry.names() == ["httpx", "katana", "subfinder"]


def test_registry_sources_for_linux_amd64_are_wellformed() -> None:
    registry = ToolRegistry()
    for spec in registry.all():
        source = spec.source_for("linux/amd64")
        assert source is not None
        assert source.url.startswith("https://github.com/projectdiscovery/")
        assert source.url.endswith(f"{spec.name}_{spec.version}_linux_amd64.zip")
        assert source.archive_member == spec.name


def test_registry_checksum_urls_are_correct() -> None:
    """Regression test to ensure subfinder/httpx/katana checksum URLs match GitHub's actual filenames.

    This prevents future regressions like katana v1.6.1's hyphen-separated filename."""
    registry = ToolRegistry()

    # Subfinder uses underscore separator
    subfinder = registry.get("subfinder")
    subfinder_source = subfinder.source_for("linux/amd64")
    assert subfinder_source is not None
    assert subfinder_source.checksums_url == (
        "https://github.com/projectdiscovery/subfinder/releases/download/v2.14.0/subfinder_2.14.0_checksums.txt"
    )

    # Httpx uses underscore separator
    httpx = registry.get("httpx")
    httpx_source = httpx.source_for("linux/amd64")
    assert httpx_source is not None
    assert httpx_source.checksums_url == (
        "https://github.com/projectdiscovery/httpx/releases/download/v1.9.0/httpx_1.9.0_checksums.txt"
    )

    # Katana uses hyphen separator
    katana = registry.get("katana")
    katana_source = katana.source_for("linux/amd64")
    assert katana_source is not None
    assert katana_source.checksums_url == (
        "https://github.com/projectdiscovery/katana/releases/download/v1.6.1/katana-1.6.1-checksums.txt"
    )


def test_registry_unknown_tool_raises() -> None:
    with pytest.raises(ToolNotInRegistryError):
        ToolRegistry().get("nuclei")


# --- Executor ----------------------------------------------------------------
def test_executor_runs_real_process() -> None:
    executor = ToolExecutor()
    result = executor.run(Path(sys.executable), ["--version"])
    assert isinstance(result, ToolExecutionResult)
    assert result.ok
    assert result.returncode == 0
    assert "Python" in (result.stdout + result.stderr)


def test_executor_captures_nonzero_exit() -> None:
    executor = ToolExecutor()
    result = executor.run(Path(sys.executable), ["-c", "import sys; sys.exit(3)"])
    assert not result.ok
    assert result.returncode == 3


# --- Provider checksum verification ------------------------------------------
def _zip_bytes(member: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, content)
    return buf.getvalue()


def test_provider_rejects_checksum_mismatch(tmp_path: Path) -> None:
    from app.infrastructure.tools.provider import GitHubReleaseProvider

    provider = GitHubReleaseProvider()
    payload = _zip_bytes("subfinder", b"#!/bin/sh\necho hi\n")
    source = BinarySource(
        url="https://example.com/subfinder_9.9.9_linux_amd64.zip",
        archive_format="zip",
        archive_member="subfinder",
        sha256="0" * 64,  # deliberately wrong
    )
    # Patch the network fetch to return our in-memory zip.
    provider_module = sys.modules["app.infrastructure.tools.provider"]
    original = provider_module._http_get
    provider_module._http_get = lambda url: payload  # type: ignore[assignment]
    try:
        spec = ToolSpec("subfinder", "9.9.9", "test", {"linux/amd64": source})
        with pytest.raises(ChecksumMismatchError):
            provider.install(spec, source, tmp_path / "subfinder")
    finally:
        provider_module._http_get = original  # type: ignore[assignment]


def test_provider_installs_with_pinned_checksum(tmp_path: Path) -> None:
    from app.infrastructure.tools.provider import GitHubReleaseProvider

    provider = GitHubReleaseProvider()
    payload = _zip_bytes("subfinder", b"#!/bin/sh\necho hi\n")
    correct = hashlib.sha256(payload).hexdigest()
    source = BinarySource(
        url="https://example.com/subfinder_9.9.9_linux_amd64.zip",
        archive_format="zip",
        archive_member="subfinder",
        sha256=correct,
    )
    provider_module = sys.modules["app.infrastructure.tools.provider"]
    original = provider_module._http_get
    provider_module._http_get = lambda url: payload  # type: ignore[assignment]
    try:
        spec = ToolSpec("subfinder", "9.9.9", "test", {"linux/amd64": source})
        installed = provider.install(spec, source, tmp_path / "subfinder")
        assert installed.sha256 == correct
        assert installed.path.exists()
        assert installed.path.read_bytes() == b"#!/bin/sh\necho hi\n"
    finally:
        provider_module._http_get = original  # type: ignore[assignment]


# --- Manager (with a fake provider, no network) ------------------------------
class _FakeProvider(ToolProvider):
    def install(self, spec, source, dest_dir) -> InstalledTool:
        dest_dir.mkdir(parents=True, exist_ok=True)
        binary = dest_dir / spec.name
        binary.write_text("#!/bin/sh\necho fake\n")
        binary.chmod(0o755)
        return InstalledTool(spec.name, spec.version, binary, "deadbeef")


def _manager(tmp_path: Path) -> ToolManager:
    return ToolManager(
        tools_dir=tmp_path,
        registry=ToolRegistry(),
        provider=_FakeProvider(),
        platform_key="linux/amd64",
    )


def test_manager_status_all_missing_initially(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    statuses = manager.status()
    assert {s.name for s in statuses} == {"subfinder", "httpx", "katana"}
    assert all(not s.installed for s in statuses)
    assert all(s.needs_install for s in statuses)


def test_manager_install_is_idempotent_and_resolves(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    first = manager.install("subfinder")
    assert manager.is_installed("subfinder")
    assert manager.resolve_path("subfinder") == first.path
    # Second call short-circuits (already installed) and returns metadata.
    again = manager.install("subfinder")
    assert again.version == first.version


def test_manager_resolve_missing_raises(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    with pytest.raises(ToolNotInstalledError):
        manager.resolve_path("httpx")


def test_manager_install_all_then_run(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    installed = manager.install_all()
    assert len(installed) == 3
    # The fake binary is a shell script; running it is platform-dependent, so we
    # only assert resolution + status here.
    assert all(manager.is_installed(name) for name in ("subfinder", "httpx", "katana"))
