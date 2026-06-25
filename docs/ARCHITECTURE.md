# ARCHITECTURE

HunterAI's backend follows **Clean Architecture**. Dependencies point inward only:

```
            ┌─────────────────────────────────────────────┐
            │                 interfaces                   │  FastAPI routers, schemas
            │     (HTTP delivery — knows about the web)    │
            ├─────────────────────────────────────────────┤
            │               infrastructure                 │  tools, recon, scanner,
            │   (implements ports: DB, subprocess, I/O)    │  persistence, execution
            ├─────────────────────────────────────────────┤
            │                application                   │  use cases (orchestration)
            ├─────────────────────────────────────────────┤
            │                  domain                      │  entities + ports (pure)
            └─────────────────────────────────────────────┘
                 core: config + logging (cross-cutting)

Dependency rule:  domain ← application ← infrastructure / interfaces
Inner layers NEVER import outer layers.
```

## Layers

### domain (`app/domain/`) — pure, no framework imports
- **entities/** value objects + small state machines:
  - `target.py` — `Target` (+ `normalize_domain`)
  - `recon.py` — `Subdomain`, `HttpService`, `Endpoint`
  - `scan.py` — `Scan` (PENDING→RUNNING→COMPLETED|FAILED) + `findings`
  - `finding.py` — `Finding`, `Severity` (ordered), `Confidence`
  - `scanner.py` — `PluginMetadata`, `PluginCategory`, `ScanContext`,
    `PluginExecution`, `ScanEngineResult`
  - `tool.py` — `ToolExecutionResult`
- **ports/** Protocols (interfaces) implemented by infrastructure:
  - `recon.py` — `SubdomainEnumerator`, `HttpProber`, `EndpointCrawler`
  - `scanner.py` — `ScannerPlugin` (the plugin contract)
  - `tools.py` — `ToolManagerPort`, `ToolExecutorPort`
  - `persistence.py` — `TargetRepository`, `ScanRepository`

### application (`app/application/`) — orchestration, depends only on domain
- `ports.py` — `ScanRunner` (background execution abstraction)
- `use_cases/run_recon.py` — `RunReconUseCase` (subfinder→httpx→katana ordering)
- `use_cases/run_vulnerability_scan.py` — `ScannerEngine` (runs plugins, isolates
  failures, aggregates findings)
- `use_cases/run_scan.py` — `RunScanUseCase` (composes recon + engine)
- `use_cases/start_scan.py` — `StartScanUseCase` (create target+scan, schedule)

### infrastructure (`app/infrastructure/`) — concrete implementations
- **tools/** — Tool Management: `registry`, `provider`, `manager`, `executor`,
  `models`, `errors`, `factory`. (See `TOOLCHAIN.md`.)
- **recon/** — adapters implementing recon ports: `pipeline.py`
  (Subfinder/Httpx/Katana adapters), `parsers.py`.
- **scanner/** — plugin framework: `registry.py` (`@register_plugin`,
  `discover_plugins`, `ScannerRegistry`), `base.py` (`BaseScannerPlugin`),
  `factory.py` (`build_scanner_engine`), `errors.py`, `plugins/` (extension point,
  **empty** in M2).
- **persistence/** — `database.py` (sync engine/session), `models.py` (ORM),
  `repositories.py` (domain↔ORM mapping).
- **execution/** — `BackgroundTasksScanRunner` + `execute_scan` (composition root
  for one background run).

### interfaces (`app/interfaces/api/`) — HTTP delivery
- `router.py` aggregates routers; `routes/` = `health`, `tools`, `scans`;
  `schemas/scan.py` request/response models; `deps.py` dependency providers.

### core (`app/core/`) — cross-cutting
- `config.py` — typed `Settings` (env prefix `HUNTERAI_`); `get_settings()` cached.
- `logging.py` — `configure_logging`, `get_logger`.

## Key flows

### Scan lifecycle (request → background → poll)
```
POST /scans ─► StartScanUseCase: Target.create + Scan(RUNNING) persisted
            └─► ScanRunner.run_in_background(scan_id)   [FastAPI BackgroundTasks]
                    │
                    ▼ (after response)
            execute_scan(scan_id)  [own DB session — composition root]
              ├─ build recon pipeline (ToolManager) + RunReconUseCase
              ├─ build scanner engine (resilient: empty engine on discovery error)
              └─ RunScanUseCase.execute(target, scan):
                   recon → (if COMPLETED) ScanContext.from_scan → ScannerEngine.run
                   → attach findings → mark_completed
              └─ repo.update(scan)   [single write; status COMPLETED only when done]
GET /scans/{id}  ─► repo.get → ScanDetailResponse  (frontend polls until terminal)
```

### Dependency inversion seams (why extension is cheap)
- **Recon stages** are 1-method Protocols → swap Subfinder for another enumerator
  without touching the use case.
- **Scanner plugins** implement `ScannerPlugin`; the engine depends on the
  Protocol only → add a plugin as one new file (see `PLUGIN_DEVELOPMENT.md`).
- **Execution backend** is the `ScanRunner` port → swap BackgroundTasks for
  Celery/RQ later without changing the API or use cases.
- **Tools** are declared in a registry → add Nuclei/ffuf/Naabu via one entry.

## Conventions

- `from __future__ import annotations` in every module.
- Pure value objects: frozen `@dataclass(slots=True)`.
- Ports are `typing.Protocol`.
- Use cases: constructor-injected collaborators, single `execute()`/`run()`, a
  `clock`/`timer` injected for testability.
- Failures are isolated and converted to terminal state, never swallowed silently
  (logged via `get_logger`).
- Tests use fakes implementing the ports; DB tests use in-memory SQLite
  (`StaticPool`).
