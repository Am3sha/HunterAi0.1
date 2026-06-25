"""Exceptions for the scanner subsystem."""

from __future__ import annotations


class ScannerError(Exception):
    """Base class for scanner-subsystem errors."""


class PluginNotFoundError(ScannerError):
    """Requested plugin is not registered."""


class DuplicatePluginError(ScannerError):
    """A plugin with the same name is already registered."""
