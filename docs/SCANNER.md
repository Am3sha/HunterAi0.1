# Scanner Engine (Sprint 1, Milestone 1)

HunterAI's vulnerability scanning is a **plugin-based engine**. Each vulnerability
check is an independent plugin; the engine runs the selected plugins against a
target's attack surface and aggregates their findings. Adding a new scanner is
**one new file** — no changes to the engine or existing plugins (dependency
inversion + discovery).

> Milestone 1 is the **framework only**: no AI, no report generation, and no real
> vulnerability plugins are shipped. The `plugins/` package is the extension point
> for later milestones.

## Pillars (Clean Architecture)

| Pillar | Location | Layer | Responsibility |
|--------|----------|-------|----------------|
| `ScannerPlugin` (Protocol) | `domain/ports/scanner.py` | domain | The plugin contract. |
| `Finding`, `ScanContext`, `PluginMetadata`, `ScanEngineResult` | `domain/entities/finding.py`, `domain/entities/scanner.py` | domain | Pure value objects. |
| `ScannerEngine` | `application/use_cases/run_vulnerability_scan.py` | application | Orchestrates plugins, isolates failures, aggregates findings. |
| `ScannerRegistry`, `register_plugin`, `discover_plugins` | `infrastructure/scanner/registry.py` | infrastructure | Discover/register/select plugins. |
| `BaseScannerPlugin` | `infrastructure/scanner/base.py` | infrastructure | Convenience base for writing plugins. |
| `build_scanner_engine` | `infrastructure/scanner/factory.py` | infrastructure | Wire registry → engine. |

**Dependency rule:** the engine depends only on the `ScannerPlugin` port and
domain value objects. It never imports a concrete plugin. Plugins depend on the
domain entities/base, never on the engine.

## Data flow

```
recon Scan ──► ScanContext ──► ScannerEngine.run() ──► ScanEngineResult
(services,       (attack         runs each selected      (findings[],
 endpoints,       surface)        plugin in isolation)     executions[])
 subdomains)
```

- `ScanContext` is the immutable attack surface handed to every plugin (built via
  `ScanContext.from_scan(scan)`). Immutability means one plugin can't affect
  another through shared state.
- `ScannerEngine.run()` executes each plugin, **isolating exceptions**: a failing
  plugin is recorded as `FAILED` and never aborts the run. It times each plugin
  and returns a `ScanEngineResult` with all findings plus per-plugin
  `PluginExecution` records.
- `ScanEngineResult` offers `total_findings`, `counts_by_severity`,
  `failed_plugins`, and `sorted_findings()` (severity-ranked).

## Findings

A `Finding` carries: `plugin`, `name`, `severity` (`info`→`critical`, ordered via
`Severity.rank`), `target`, `description`, `confidence`, `evidence`,
`references`, and free-form `metadata`.

## Writing a plugin

Create one file under `app/infrastructure/scanner/plugins/`:

```python
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
        for service in context.services:
            # ... inspect the service, build findings ...
            # findings.append(self.build_finding(name=..., severity=Severity.LOW,
            #                                     target=service.url, ...))
            pass
        return findings
```

`discover_plugins()` imports every module in the package so the `@register_plugin`
decorators run; `build_default_registry()` then instantiates them. No existing
code changes are required.

## Selecting which plugins run

`ScannerRegistry.select(enabled=..., disabled=...)`:
- `enabled` (allow-list): only these plugin names are considered;
- otherwise plugins with `default_enabled=True` are considered;
- `disabled` (deny-list) is subtracted last.

`build_scanner_engine(enabled=..., disabled=...)` applies this and returns a ready
engine.

## CLI

```bash
python -m app.scanner_cli list     # list discovered plugins (none in M1)
```

## What is NOT in Milestone 1

- No real vulnerability plugins (the framework only).
- No AI.
- No report generation.
- No wiring into the scan flow / API / persistence yet (later milestones).

---

## Milestone 2 — pipeline integration (done)

The engine is now wired into the scan flow. A scan runs **recon, then scanning**,
in a single run; findings attach to the same `scan_id` the frontend already polls.

- **Orchestration:** `application/use_cases/run_scan.py` — `RunScanUseCase`
  composes `RunReconUseCase` + `ScannerEngine`. After recon completes it builds a
  `ScanContext` from the scan and runs the engine, attaching the findings. If
  recon fails, scanning is skipped.
- **Composition root:** `infrastructure/execution/execute_scan` builds the recon
  pipeline + scanner engine and runs `RunScanUseCase`. Building the engine is
  resilient — a plugin-discovery failure degrades to an empty engine so recon
  results are never lost.
- **Persistence:** new `findings` table (`FindingModel`), mapped in the scan
  repository; Alembic migration `0002_findings`. (The ORM column is `meta`, since
  `metadata` is reserved on SQLAlchemy declarative models.)
- **API:** `GET /scans/{id}` now returns a `findings[]` array, and `counts`
  includes a `findings` total.

Because M1 ships no plugins, a scan currently produces **zero findings** — the
end-to-end path is proven and ready for real plugins in M3. Frontend display of
findings is deferred to M4.

> After adding the `findings` table, run `alembic upgrade head` (or
> `python -m app.db_cli init` on a fresh dev database).
