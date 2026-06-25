"""Scanner Registry — catalog of available scanner plugins.

Two complementary ways to populate it:

1. **Decorator + discovery (production).** A plugin module under
   ``app/infrastructure/scanner/plugins/`` decorates its class with
   ``@register_plugin``. ``build_default_registry()`` imports every module in that
   package (so the decorators run) and instantiates the registered plugins.
   Adding a scanner is therefore *one new file* — no existing code changes.

2. **Direct construction (tests / explicit wiring).** ``ScannerRegistry(plugins)``
   takes ready-made plugin instances.

``select()`` resolves which plugins to actually run, honouring an optional
allow/deny list and each plugin's ``default_enabled`` flag.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable

from app.core.logging import get_logger
from app.domain.ports.scanner import ScannerPlugin
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.errors import DuplicatePluginError, PluginNotFoundError

logger = get_logger(__name__)

# Classes registered via the @register_plugin decorator, keyed by plugin name.
_REGISTERED: dict[str, type[BaseScannerPlugin]] = {}


def register_plugin(cls: type[BaseScannerPlugin]) -> type[BaseScannerPlugin]:
    """Class decorator that registers a plugin for default discovery."""
    name = cls.metadata.name
    existing = _REGISTERED.get(name)
    if existing is not None and existing is not cls:
        raise DuplicatePluginError(f"Plugin name '{name}' is already registered")
    _REGISTERED[name] = cls
    return cls


def discover_plugins() -> None:
    """Import every module in the plugins package so decorators run."""
    from app.infrastructure.scanner import plugins as plugins_pkg

    for module_info in pkgutil.iter_modules(plugins_pkg.__path__):
        importlib.import_module(f"{plugins_pkg.__name__}.{module_info.name}")


class ScannerRegistry:
    """Read/registerable catalog of scanner plugin instances."""

    def __init__(self, plugins: Iterable[ScannerPlugin] = ()) -> None:
        self._plugins: dict[str, ScannerPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: ScannerPlugin) -> None:
        name = plugin.metadata.name
        if name in self._plugins:
            raise DuplicatePluginError(f"Plugin name '{name}' is already registered")
        self._plugins[name] = plugin

    def get(self, name: str) -> ScannerPlugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise PluginNotFoundError(
                f"Plugin '{name}' is not registered. Known: {', '.join(self.names()) or 'none'}"
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._plugins

    def names(self) -> list[str]:
        return sorted(self._plugins)

    def all(self) -> list[ScannerPlugin]:
        return [self._plugins[name] for name in self.names()]

    def select(
        self,
        *,
        enabled: Iterable[str] | None = None,
        disabled: Iterable[str] | None = None,
    ) -> list[ScannerPlugin]:
        """Resolve plugins to run.

        - ``enabled`` (allow-list): if given, only these names are considered.
        - otherwise plugins with ``default_enabled=True`` are considered.
        - ``disabled`` (deny-list) is always subtracted last.
        """
        allow = set(enabled) if enabled is not None else None
        deny = set(disabled or ())
        selected: list[ScannerPlugin] = []
        for name in self.names():
            plugin = self._plugins[name]
            if name in deny:
                continue
            if allow is not None:
                if name in allow:
                    selected.append(plugin)
            elif plugin.metadata.default_enabled:
                selected.append(plugin)
        return selected


def build_default_registry() -> ScannerRegistry:
    """Discover plugins and build a registry of fresh instances."""
    discover_plugins()
    plugins = [cls() for cls in _REGISTERED.values()]
    logger.info("Scanner registry built with %d plugin(s)", len(plugins))
    return ScannerRegistry(plugins)
