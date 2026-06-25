# ROADMAP

High-level direction. HunterAI evolves from a recon tool → modular vulnerability
scanner → AI-assisted assistant. Built in **small, reviewable milestones**; stop
for review after each.

## Sprint 0 — Reconnaissance MVP ✅ (complete)
Clean foundation: tool management, recon pipeline, persistence, API, frontend.
See `SPRINT_0_SUMMARY.md`.

## Sprint 1 — Modular Vulnerability Scanner (in progress)
Goal: transform the recon framework into a modular vulnerability scanner.

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Plugin-based scanner engine (framework only) | ✅ done |
| M2 | Integrate engine into the scan pipeline (persist + API findings) | ✅ done |
| M3 | First real scanner plugins (e.g. security-headers, cookie/TLS misconfig) | ⏳ next |
| M4 | Frontend findings display (severity-grouped) | planned |

Detail: `SPRINT_1_PLAN.md`.

## Sprint 2 — Depth & usability (tentative)
- More plugins (tech-specific checks, exposed files/dirs via ffuf, Nuclei templates).
- Plugin enable/disable + per-scan configuration via API/UI.
- Findings filtering/sorting, dedup, severity rollups in UI.
- Begin the knowledge base (see `KNOWLEDGE_BASE_PLAN.md`).

## Sprint 3+ — Reporting & evidence (tentative)
- Professional report generation (Markdown/PDF) from findings + evidence ledger.
- Evidence capture (request/response) attached to findings for reproducibility.

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
