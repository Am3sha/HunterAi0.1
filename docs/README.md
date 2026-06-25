# HunterAI — Documentation Index

Canonical project knowledge. **New session? Read `PROJECT_STATE.md` first** — it
has the "Resume Here" section and current status.

## Core (read in this order)
1. **[PROJECT_STATE.md](PROJECT_STATE.md)** — where we are now; how to run; resume here.
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** — Clean Architecture layers, flows, conventions.
3. **[ROADMAP.md](ROADMAP.md)** — sprints and direction.
4. **[DECISIONS.md](DECISIONS.md)** — ADR log: every important choice + why.

## Reference
- **[API_REFERENCE.md](API_REFERENCE.md)** — endpoints, schemas, scan lifecycle.
- **[DATABASE.md](DATABASE.md)** — schema, migrations, how to add tables.
- **[TOOLCHAIN.md](TOOLCHAIN.md)** — managed security tools + dev toolchain + env vars.
- **[SCANNER.md](SCANNER.md)** — scanner engine internals.
- **[PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md)** — how to add a scanner plugin (M3+).
- **[TOOLS.md](TOOLS.md)** — Tool Management subsystem detail.
- **[API.md](API.md)** — original API notes (see API_REFERENCE for the canonical view).

## Sprints
- **[SPRINT_0_SUMMARY.md](SPRINT_0_SUMMARY.md)** — recon MVP (complete).
- **[SPRINT0.md](SPRINT0.md)** — original Sprint 0 milestone doc.
- **[SPRINT_1_PLAN.md](SPRINT_1_PLAN.md)** — vulnerability scanner sprint (M1/M2 done, M3 next).

## Forward-looking plans (not implemented)
- **[KNOWLEDGE_BASE_PLAN.md](KNOWLEDGE_BASE_PLAN.md)** — memory/knowledge layer plan.
- **[AGENTS_FUTURE.md](AGENTS_FUTURE.md)** — AI/agent layer plan + safety prerequisites.

---
_Keep docs in sync with code. When you change behavior, update the relevant
reference file and add an ADR to `DECISIONS.md` if it's a decision. `PROJECT_STATE.md`
should reflect reality at the end of every milestone._
