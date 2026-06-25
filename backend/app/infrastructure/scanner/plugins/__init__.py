"""Scanner plugins package.

Each module here defines one vulnerability scanner plugin: a class that
subclasses ``BaseScannerPlugin`` (or satisfies the ``ScannerPlugin`` Protocol)
and is decorated with ``@register_plugin``. ``discover_plugins()`` imports every
module in this package so the decorators run at startup.

To add a scanner (no existing code changes required)::

    # app/infrastructure/scanner/plugins/security_headers.py
    from app.domain.entities.finding import Severity
    from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
    from app.infrastructure.scanner.base import BaseScannerPlugin
    from app.infrastructure.scanner.registry import register_plugin

    @register_plugin
    class SecurityHeadersScanner(BaseScannerPlugin):
        metadata = PluginMetadata(
            name="security-headers",
            title="Missing security headers",
            category=PluginCategory.MISCONFIGURATION,
        )

        def scan(self, context: ScanContext):
            findings = []
            # ... inspect context.services ...
            return findings

Sprint 1 Milestone 1 intentionally ships **no** real vulnerability plugins —
this package is the (empty) extension point for later milestones.
"""
