"""Tests for the ScannerRegistry, registration decorator, and engine factory."""

from __future__ import annotations

import pytest

from app.domain.entities.finding import Finding
from app.domain.entities.scanner import PluginMetadata, ScanContext
from app.infrastructure.scanner import (
    BaseScannerPlugin,
    ScannerRegistry,
    build_scanner_engine,
    register_plugin,
)
from app.infrastructure.scanner.errors import DuplicatePluginError, PluginNotFoundError
from app.infrastructure.scanner.registry import _REGISTERED


class _Plugin(BaseScannerPlugin):
    metadata = PluginMetadata(name="unit-a", title="A")

    def scan(self, context: ScanContext) -> list[Finding]:
        return []


class _DisabledPlugin(BaseScannerPlugin):
    metadata = PluginMetadata(name="unit-b", title="B", default_enabled=False)

    def scan(self, context: ScanContext) -> list[Finding]:
        return []


def test_register_and_get() -> None:
    registry = ScannerRegistry([_Plugin(), _DisabledPlugin()])
    assert registry.names() == ["unit-a", "unit-b"]
    assert registry.has("unit-a")
    assert registry.get("unit-a").metadata.name == "unit-a"


def test_get_unknown_raises() -> None:
    with pytest.raises(PluginNotFoundError):
        ScannerRegistry().get("nope")


def test_duplicate_registration_raises() -> None:
    registry = ScannerRegistry([_Plugin()])
    with pytest.raises(DuplicatePluginError):
        registry.register(_Plugin())


def test_select_defaults_to_default_enabled() -> None:
    registry = ScannerRegistry([_Plugin(), _DisabledPlugin()])
    selected = {p.metadata.name for p in registry.select()}
    assert selected == {"unit-a"}  # unit-b is default_enabled=False


def test_select_allow_and_deny_lists() -> None:
    registry = ScannerRegistry([_Plugin(), _DisabledPlugin()])
    # explicit allow-list overrides default_enabled
    assert {p.metadata.name for p in registry.select(enabled=["unit-b"])} == {"unit-b"}
    # deny-list subtracts
    assert registry.select(disabled=["unit-a"]) == []


def test_register_plugin_decorator_populates_global_registry() -> None:
    @register_plugin
    class _Decorated(BaseScannerPlugin):
        metadata = PluginMetadata(name="unit-decorated", title="D")

        def scan(self, context: ScanContext) -> list[Finding]:
            return []

    try:
        assert "unit-decorated" in _REGISTERED
        assert _REGISTERED["unit-decorated"] is _Decorated
    finally:
        _REGISTERED.pop("unit-decorated", None)


def test_build_scanner_engine_with_custom_registry() -> None:
    registry = ScannerRegistry([_Plugin(), _DisabledPlugin()])
    engine = build_scanner_engine(registry=registry)
    assert engine.plugin_names == ["unit-a"]  # only default-enabled selected


def test_build_default_registry_does_not_crash_with_no_plugins() -> None:
    # Milestone 1 ships no real plugins; discovery must still succeed.
    from app.infrastructure.scanner import build_default_registry

    registry = build_default_registry()
    assert isinstance(registry, ScannerRegistry)
