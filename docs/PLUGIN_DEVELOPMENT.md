# PLUGIN_DEVELOPMENT

How to add a vulnerability scanner plugin. **A plugin is one new file** under
`backend/app/infrastructure/scanner/plugins/` — no edits to the engine or other
plugins (dependency inversion + discovery).

Read alongside `docs/SCANNER.md` (engine internals) and `ARCHITECTURE.md`.

## The contract

A plugin satisfies the `ScannerPlugin` Protocol (`app/domain/ports/scanner.py`):

```python
class ScannerPlugin(Protocol):
    metadata: PluginMetadata
    def scan(self, context: ScanContext) -> list[Finding]: ...
```

Easiest path: subclass `BaseScannerPlugin` and use `@register_plugin`.

## Anatomy of a plugin

```python
# backend/app/infrastructure/scanner/plugins/security_headers.py
from __future__ import annotations

from app.domain.entities.finding import Finding, Severity, Confidence
from app.domain.entities.scanner import PluginCategory, PluginMetadata, ScanContext
from app.infrastructure.scanner.base import BaseScannerPlugin
from app.infrastructure.scanner.registry import register_plugin


@register_plugin
class SecurityHeadersScanner(BaseScannerPlugin):
    metadata = PluginMetadata(
        name="security-headers",                 # stable unique id
        title="Missing security headers",
        description="Flags absent HTTP security headers.",
        category=PluginCategory.MISCONFIGURATION,
        version="0.1.0",
        default_enabled=True,
    )

    def scan(self, context: ScanContext) -> list[Finding]:
        findings: list[Finding] = []
        for service in context.services:
            # ... inspect the service / make a request / check evidence ...
            findings.append(
                self.build_finding(                # plugin name auto-filled
                    name="Missing Content-Security-Policy",
                    severity=Severity.LOW,
                    target=service.url,
                    description="No CSP header present.",
                    confidence=Confidence.HIGH,
                    evidence="response had no content-security-policy header",
                    references=["https://owasp.org/www-project-secure-headers/"],
                    metadata={"header": "content-security-policy"},
                )
            )
        return findings
```

That's it. `discover_plugins()` imports every module in the `plugins/` package, the
`@register_plugin` decorator registers the class, and `build_default_registry()`
instantiates it. No other file changes.

## What the plugin receives — `ScanContext`

Immutable attack surface built from recon results (`ScanContext.from_scan`):
- `target_domain: str`
- `services: tuple[HttpService, ...]` (live HTTP services; `.service_urls` helper)
- `endpoints: tuple[Endpoint, ...]` (`.endpoint_urls` helper)
- `subdomains: tuple[Subdomain, ...]`

Immutability means plugins can't affect each other through shared state.

## What the plugin returns — `Finding`

Fields: `plugin`, `name`, `severity` (`Severity` enum, ordered), `target`,
`description`, `confidence` (`Confidence`), `evidence`, `references` (tuple),
`metadata` (dict), plus **Sprint 2 M2 additions**:
- `cvss: Cvss | None` — CVSS version, vector, base score (all optional)
- `cwe_ids: tuple[str, ...]` — CWE identifiers (tuple for immutability)
- `owasp_categories: tuple[str, ...]` — OWASP categories (tuple)
- `remediation: str | None` — free-text remediation guidance

Use `self.build_finding(...)` to auto-fill `plugin`. Extended signature:

```python
self.build_finding(
    name="...",
    severity=Severity.HIGH,
    target=service.url,
    cvss=Cvss(version="3.1", vector="...", base_score=7.5),
    cwe_ids=["CWE-79"],
    owasp_categories=["A03:2021-Injection"],
    remediation="Encode output.",
)
```

## Guidelines

- **Authorized testing only.** Plugins must respect scope and avoid destructive
  actions. Prefer detection over exploitation in this stage of the project.
- **Be resilient.** If a check can't run for one service, skip it — don't raise.
  (The engine isolates exceptions, recording the plugin as FAILED, but you still
  lose that plugin's other findings for the run.)
- **Network I/O:** plugins may make their own HTTP requests today. Keep timeouts
  tight. (A shared HTTP client / rate-limit gateway is a future addition.)
- **Severity discipline:** reserve HIGH/CRITICAL for confirmed, impactful issues;
  use INFO/LOW for hygiene/observations.
- **Stable `name`:** the metadata `name` is the plugin's identity (registry key,
  persisted on findings). Don't rename casually.
- **`default_enabled=False`** for noisy/experimental plugins; they then run only
  when explicitly enabled.

## Selecting which plugins run

`ScannerRegistry.select(enabled=..., disabled=...)`:
- `enabled` allow-list → only those names;
- else plugins with `default_enabled=True`;
- `disabled` deny-list subtracted last.

`build_scanner_engine(enabled=..., disabled=...)` applies this.

## Testing a plugin

Unit-test the class directly with a hand-built `ScanContext` (no engine, no DB):

```python
def test_flags_missing_csp():
    ctx = ScanContext(target_domain="example.com",
                      services=(HttpService(url="https://example.com", status_code=200),))
    findings = SecurityHeadersScanner().scan(ctx)
    assert any(f.name.startswith("Missing") for f in findings)
```

Also add an engine-level test if behavior depends on aggregation. See
`tests/test_scanner_engine.py` and `tests/test_run_scan.py` for patterns.

## CLI

```bash
python -m app.scanner_cli list   # shows discovered plugins
```

## Checklist for a new plugin
1. New file in `infrastructure/scanner/plugins/` with `@register_plugin`.
2. Unique `metadata.name`; sensible `category`, `default_enabled`.
3. Pure, resilient `scan()`; use `build_finding`.
4. Unit test (+ engine test if needed).
5. `python -m app.scanner_cli list` shows it; `pytest -q` green.
6. Note it in `SPRINT_1_PLAN.md` / `ROADMAP.md` if it's a planned deliverable.
