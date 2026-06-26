# SPRINT_1_PLAN — Modular Vulnerability Scanner

**Goal:** transform HunterAI from a recon framework into a modular vulnerability
scanner — without breaking Clean Architecture, modularity, or the test philosophy.

## Milestones

### M1 — Plugin-based scanner engine (framework only) ✅ done
Built the engine with dependency inversion; **no real plugins, no AI, no reports.**
- Domain: `Finding`/`Severity`/`Confidence`; `ScanContext`, `PluginMetadata`,
  `PluginExecution`, `ScanEngineResult`; `ScannerPlugin` port.
- Application: `ScannerEngine` (runs plugins, isolates failures, aggregates).
- Infrastructure: `BaseScannerPlugin`, `ScannerRegistry` + `@register_plugin` +
  `discover_plugins`, `build_scanner_engine`, empty `plugins/` package.
- Tests + `docs/SCANNER.md` + `scanner_cli`. (53/53 at the time.)

### M2 — Integrate engine into the scan pipeline ✅ done
Findings attach to the **same scan_id** the frontend already polls (extend existing
scan; no separate resource).
- `RunScanUseCase` composes recon + engine; `execute_scan` runs it (resilient
  engine build).
- `Scan.findings` + `counts["findings"]`; `FindingModel` table + repository mapping
  + Alembic `0002_findings`.
- API: `GET /scans/{id}` returns `findings[]`.
- 56/56 tests. **Findings empty until M3** (no plugins yet).

### M3 — First real scanner plugins ✅ done
Implement the first genuine detections using the M2 pipeline. Each plugin is **one
new file** under `infrastructure/scanner/plugins/` (see `PLUGIN_DEVELOPMENT.md`).

Candidate plugins (confirm scope at M3 kickoff):
- `security-headers` — missing/weak HTTP security headers (CSP, HSTS,
  X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
- `cookie-flags` — cookies missing Secure/HttpOnly/SameSite.
- `tls-misconfig` — basic TLS hygiene (e.g. missing HSTS on HTTPS, plaintext HTTP).
- (stretch) `exposed-files` — common sensitive paths (e.g. `/.git/`, `/.env`)
  using discovered endpoints/services.

Design notes for M3:
- Plugins consume `ScanContext.services` / `.endpoints`; may make their own bounded
  HTTP requests (tight timeouts). A shared HTTP client / rate-limit gateway is a
  later concern — keep requests minimal and authorized-scope only.
- Severity discipline (ADR mindset): hygiene = INFO/LOW; confirmed impactful =
  HIGH/CRITICAL.
- Unit-test each plugin directly with a hand-built `ScanContext`; no engine/DB
  needed. Add engine/integration coverage if aggregation matters.
- No existing files change except adding plugin modules (+ their tests).

**Exit criteria:** ≥1 real plugin produces findings end-to-end (visible via
`GET /scans/{id}`), `scanner_cli list` shows them, all tests green. Stop for review.

### M4 — Frontend findings display (planned)
Severity-grouped findings section in the UI (new `components/scan/` pieces + table),
wired to the existing `findings[]` in the scan detail response. No backend change
expected.

## Constraints (unchanged from Sprint 0)
No AI. No reporting. No auth. No browser automation. Authorized testing only.
Small reviewable milestones; preserve architecture and coding style.
