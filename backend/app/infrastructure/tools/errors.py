"""Exceptions for the Tool Management subsystem."""

from __future__ import annotations


class ToolError(Exception):
    """Base class for all tool-management errors."""


class ToolNotInRegistryError(ToolError):
    """Requested tool has no entry in the Tool Registry."""


class UnsupportedPlatformError(ToolError):
    """No binary source is registered for the current OS/architecture."""


class DownloadError(ToolError):
    """A binary or checksum file could not be downloaded."""


class ChecksumMismatchError(ToolError):
    """The downloaded asset's SHA-256 did not match the expected value."""


class ExtractionError(ToolError):
    """The downloaded archive could not be extracted / the binary was not found."""


class ToolNotInstalledError(ToolError):
    """The tool is not present in the managed tools directory."""


class ToolExecutionError(ToolError):
    """A tool process failed to start or exited abnormally."""


class ToolTimeoutError(ToolExecutionError):
    """A tool process exceeded its allotted run time."""
