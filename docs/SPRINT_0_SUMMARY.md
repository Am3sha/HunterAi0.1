# SPRINT_0_SUMMARY — Reconnaissance MVP

**Goal:** a clean, extensible reconnaissance MVP. No AI, browser automation,
reporting, memory, or authentication.

**Outcome:** ✅ complete. Full loop: enter a domain → start scan → background recon
(Subfinder → httpx → Katana) → persist → poll → display.

Original milestone doc: `docs/SPRINT0.md`. API/tools detail: `docs/API_REFERENCE.md`,
`docs/TOOLCHAIN.md`.

## Milestones delivered

| # | Milestone | Result |
|---|-----------|--------|
| M1 | Repo scaffold + Clean Architecture skeleton | Monorepo; FastAPI boots `/health`; layered packages |
| M2 | Tool Management + setup installer | Registry/Provider/Manager/Executor; pinned, checksum-verified installs |
| M3 | Domain entities + recon pipeline use case | `Target`/`Scan`/recon entities; `RunReconUseCase`; tool adapters + parsers |
| M4 | Persistence + API (background execution) | PostgreSQL + repositories; `POST/GET /scans`; BackgroundTasks behind `ScanRunner` |
| M5 | Next.js frontend | Target input, start scan, polling, results display |

## Key components built
- **Tool Management** (`infrastructure/tools/`) — see `TOOLCHAIN.md`.
- **Recon pipeline** (`infrastructure/recon/`) — Subfinder/httpx/Katana adapters +
  tolerant parsers; orchestrated by `RunReconUseCase` (apex always probed; only
  live URLs crawled; partial results preserved on failure).
- **Persistence** (`infrastructure/persistence/`) — sync SQLAlchemy 2.0, relational
  child tables, Alembic `0001_initial`.
- **API** (`interfaces/api/`) — health, tools, scans; non-blocking create + poll.
- **Frontend** — App Router page + `use-scan` polling hook + shadcn/ui components;
  typed API client.

## Notable decisions (see DECISIONS.md)
ADR-001 Clean Architecture · ADR-002 Linux/WSL · ADR-003/004 managed tools +
integrity · ADR-006 sync SQLAlchemy · ADR-008 BackgroundTasks behind a port ·
ADR-010 relational results.

## State at end of Sprint 0
- Backend tests: 40 passing.
- Frontend: type-checks + production build pass.
- Verified path: create scan → poll → render subdomains/services/endpoints.
- Not done (carried forward): AI, vulnerability scanning, reporting, auth, memory,
  browser automation.
