"""Tool Provider — acquires a tool binary and verifies its integrity.

Responsibilities:
1. download the pinned release asset (and, if needed, its checksums file);
2. verify SHA-256 (pinned value if present, else the official checksums file);
3. extract the binary into the managed tools directory and mark it executable.

Uses only the Python standard library (``urllib``, ``zipfile``, ``tarfile``,
``hashlib``) so the runtime stays dependency-light.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.error
import urllib.request
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.logging import get_logger
from app.infrastructure.tools.errors import (
    ChecksumMismatchError,
    DownloadError,
    ExtractionError,
)
from app.infrastructure.tools.models import BinarySource, InstalledTool, ToolSpec

logger = get_logger(__name__)

_USER_AGENT = "HunterAI-ToolProvider/0.0"
_DOWNLOAD_TIMEOUT = 120  # seconds


class ToolProvider(ABC):
    """Strategy for acquiring a tool's binary."""

    @abstractmethod
    def install(self, spec: ToolSpec, source: BinarySource, dest_dir: Path) -> InstalledTool:
        """Download, verify, and place the binary; return install metadata."""


class GitHubReleaseProvider(ToolProvider):
    """Installs single-binary tools distributed as GitHub release archives."""

    def install(self, spec: ToolSpec, source: BinarySource, dest_dir: Path) -> InstalledTool:
        dest_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading %s v%s from %s", spec.name, spec.version, source.url)
        payload = _http_get(source.url)

        digest = hashlib.sha256(payload).hexdigest()
        self._verify_checksum(source, digest)

        binary_path = dest_dir / spec.name
        self._extract(source, payload, binary_path)
        binary_path.chmod(0o755)

        logger.info("Installed %s -> %s (sha256=%s)", spec.name, binary_path, digest)
        return InstalledTool(
            name=spec.name, version=spec.version, path=binary_path, sha256=digest
        )

    # -- integrity ------------------------------------------------------------
    def _verify_checksum(self, source: BinarySource, actual_sha256: str) -> None:
        if source.sha256:
            expected = source.sha256.lower()
            if actual_sha256.lower() != expected:
                raise ChecksumMismatchError(
                    f"SHA-256 mismatch for {source.asset_filename}: "
                    f"expected {expected}, got {actual_sha256}"
                )
            logger.debug("Pinned checksum verified for %s", source.asset_filename)
            return

        if source.checksums_url:
            expected = self._fetch_expected_checksum(source)
            if actual_sha256.lower() != expected.lower():
                raise ChecksumMismatchError(
                    f"SHA-256 mismatch for {source.asset_filename} (per official "
                    f"checksums): expected {expected}, got {actual_sha256}"
                )
            logger.warning(
                "Verified %s against official checksums file. Pin sha256='%s' in the "
                "registry for reproducible installs.",
                source.asset_filename,
                actual_sha256,
            )
            return

        logger.warning(
            "No checksum available for %s — integrity NOT verified.",
            source.asset_filename,
        )

    def _fetch_expected_checksum(self, source: BinarySource) -> str:
        assert source.checksums_url is not None
        text = _http_get(source.checksums_url).decode("utf-8", errors="replace")
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].lstrip("*") == source.asset_filename:
                return parts[0]
        raise ChecksumMismatchError(
            f"{source.asset_filename} not listed in checksums file {source.checksums_url}"
        )

    # -- extraction -----------------------------------------------------------
    def _extract(self, source: BinarySource, payload: bytes, dest: Path) -> None:
        if source.archive_format == "raw":
            dest.write_bytes(payload)
            return
        if source.archive_format == "zip":
            self._extract_zip(payload, source.archive_member, dest)
            return
        if source.archive_format == "tar.gz":
            self._extract_targz(payload, source.archive_member, dest)
            return
        raise ExtractionError(f"Unsupported archive format: {source.archive_format}")

    @staticmethod
    def _extract_zip(payload: bytes, member: str, dest: Path) -> None:
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            name = _match_member(zf.namelist(), member)
            if name is None:
                raise ExtractionError(
                    f"'{member}' not found in archive (members: {zf.namelist()})"
                )
            dest.write_bytes(zf.read(name))

    @staticmethod
    def _extract_targz(payload: bytes, member: str, dest: Path) -> None:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tf:
            name = _match_member(tf.getnames(), member)
            if name is None:
                raise ExtractionError(
                    f"'{member}' not found in archive (members: {tf.getnames()})"
                )
            extracted = tf.extractfile(name)
            if extracted is None:
                raise ExtractionError(f"'{name}' is not a regular file")
            dest.write_bytes(extracted.read())


def _match_member(members: list[str], wanted: str) -> str | None:
    """Find an archive member by exact name or basename match."""
    for m in members:
        if m == wanted or m.rsplit("/", 1)[-1] == wanted:
            return m
    return None


def _http_get(url: str) -> bytes:
    """Fetch a URL (follows redirects) and return the body bytes."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_DOWNLOAD_TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code} fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise DownloadError(f"Failed to fetch {url}: {exc.reason}") from exc
