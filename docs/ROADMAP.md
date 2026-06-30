# ROADMAP

High-level direction. HunterAI evolves from a recon tool → modular vulnerability
scanner → AI-assisted assistant. Built in **small, reviewable milestones**; stop
for review after each.

## Sprint 0 — Reconnaissance MVP ✅ (complete)
Clean foundation: tool management, recon pipeline, persistence, API, frontend.
See `SPRINT_0_SUMMARY.md`.

## Sprint 1 — Modular Vulnerability Scanner ✅ (complete)
Goal: transform the recon framework into a modular vulnerability scanner.

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Plugin-based scanner engine (framework only) | ✅ done |
| M2 | Integrate engine into the scan pipeline (persist + API findings) | ✅ done |
| M3 | First real scanner plugins (security-headers, cookie-security, cors, clickjacking, tls-hygiene) over a shared read-only HTTP client | ✅ done |

Frontend findings display (severity-grouped `FindingsTable`) also shipped.
Detail: `SPRINT_1_PLAN.md`.

## Sprint 2 — Professional Vulnerability Scanner (in progress)
Official approved plan. Fixed implementation order; one milestone at a time.

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Scanner infrastructure seams (HTTP timing, `ScannerConfig`, `ScanContext` tools/config DI, param utils) | ✅ done |
| M2 | Advanced Finding model (CVSS, CWE, OWASP, confidence, evidence, references, remediation, metadata) | ✅ done |
| M3 | XSS plugin (safe detection only) | ⏳ next |
| M4 | SQL Injection plugin (safe error/time-based) | planned |
| M5 | Sensitive files discovery (ffuf integration) | planned |
| M6 | Risk scoring engine | planned |
| M7 | Professional reporting (Markdown/JSON; PDF-ready) | planned |
| M8 | Dashboard improvements (filters, charts, stats) | planned |
| M9 | Knowledge base foundation (architecture only, no AI) | planned |

## Later — AI / agents (deferred, see `AGENTS_FUTURE.md`)
- Planner/orchestrator that decides next actions; specialized agents (Recon, API,
  IDOR, XSS, …); memory; supervised (human-in-the-loop) autonomy.
- **Hard prerequisite:** a non-bypassable execution/scope guard before any
  autonomous action.

## Cross-cutting (not yet scheduled)
- Authentication / multi-user.
- Scope enforcement gateway (rate limits, allow-list, kill-switch).
- Swap execution backend (BackgroundTasks → Celery/RQ) when scale requires.

## Guiding principles
1. Clean Architecture boundaries are non-negotiable.
2. Small reviewable milestones; one concern at a time.
3. Authorized testing only; safety/scope before autonomy.
4. Extensibility via ports + registries (new plugin/tool = new file, no edits).
5. Production-quality, tested code; avoid over-engineering.
