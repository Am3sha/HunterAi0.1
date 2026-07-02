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

---

## Sprint 1 M3 — live-request plugins (shipped)

Five read-only plugins now ship under `infrastructure/scanner/plugins/`:
`security_headers`, `cookie_security`, `cors`, `clickjacking`, `tls_hygiene`.
They share a **scope-enforcing, read-only HTTP client** (`HttpClient` port,
`infrastructure/http`) injected via `ScanContext.http`. See
`docs/PLUGIN_DEVELOPMENT.md`.

---

## Sprint 2 M3 — first advanced plugin (shipped)

The **reflected XSS** plugin (`xss`) now ships under
`infrastructure/scanner/plugins/`. It performs **safe, passive detection only**:
sends harmless reflection markers and checks for unencoded reflection in response
bodies. No exploitation, no bypasses, no aggressive fuzzing, no payload spraying.
It fully populates the **Sprint 2 M2 Finding model** — `cvss`, `cwe_ids`,
`owasp_categories`, and `remediation` — and respects `ScannerConfig.max_endpoints`
and request timeouts via the shared `safe_get` helper.

This brings the total to **six built-in plugins**.

---

## Sprint 2 M4 — error-based SQL Injection plugin (shipped)

The **error-based SQL injection** plugin (`sqli`) now ships under
`infrastructure/scanner/plugins/`. It performs **safe, passive detection only**:
injects benign SQL syntax markers (single quote, double quote, backtick, double
single quote) and checks for database error messages in response bodies. Supports
MySQL, PostgreSQL, SQL Server, Oracle, and SQLite error signatures. No
exploitation, no time-based payloads, no UNION attacks, no data extraction.
It fully populates the **Sprint 2 M2 Finding model** — `cvss`, `cwe_ids`,
`owasp_categories`, and `remediation` — and respects `ScannerConfig.max_endpoints`
and request timeouts via the shared `safe_get` helper.

**Finding consistency:** Confidence = Medium, Severity = Medium, CVSS = 5.3 MEDIUM
(provisional; active verification required to confirm exploitable SQLi).

This brings the total to **seven built-in plugins**.

---

## Sprint 2 M1 — infrastructure seams (shipped)

Additive architecture work to support future advanced plugins. **No behaviour
change**, no new vulnerability plugins, existing 5 plugins untouched.

- **HTTP timing.** `HttpResponse.elapsed_ms` (approx. wall-clock per request) is
  now populated by `UrllibHttpClient`. Foundation for future time-based
  heuristics; no plugin consumes it yet. Default `0.0`.
- **`ScannerConfig`** (`domain/entities/scanner_config.py`) — injectable
  limits/timeouts (`request_timeout=5.0`, `max_services=25`, `max_endpoints=50`).
  Defaults equal the historical constants, so nothing changes at runtime.
- **`ScanContext` capabilities.** Now also carries (all optional, `compare=False`):
  - `tools: ToolManagerPort | None` — managed-tool runner, injected exactly like
    `http` (prepares ffuf-based plugins; M5).
  - `config: ScannerConfig` — per-scan limits (default applied).
  - `parameterized_endpoints()` — view of endpoints with a query string (for
    future param-based plugins). Pure data view; no requests, no payloads.
- **Param utilities** (`infrastructure/scanner/plugins/_params.py`) — payload-free
  URL/query helpers: `query_params`, `param_names`, `has_query_params`,
  `with_param_value`, `base_url`. No detection logic.
- **Wiring.** `RunScanUseCase` accepts `tools` / `config` and passes them into
  `ScanContext.from_scan(...)`; `execute_scan` injects the existing `ToolManager`.

These are seams only — XSS/SQLi/ffuf/scoring/reporting are later milestones.
