# DECISIONS (ADR log)

Architecture decisions and *why*. Newest decisions can be appended at the end.
Format: short, durable rationale so future sessions don't re-litigate settled
choices.

---

### ADR-001 — Clean Architecture, modular
**Decision:** Domain/application/infrastructure/interfaces with a strict inward
dependency rule.
**Why:** The product will grow many subsystems (recon, scanner, future AI). Keeping
business logic independent of frameworks/DB/tools makes each testable and
swappable. Ports (Protocols) are the seams.

### ADR-002 — Linux-first, develop in WSL; Docker optional
**Decision:** Ubuntu/Kali primary; Windows users use WSL. Docker is optional
(compose file for Postgres only).
**Why:** The security toolchain (ProjectDiscovery binaries) is Linux-native. Repo
lives on a Windows path but all execution happens in WSL (`/mnt/e/HunterAI`).

### ADR-003 — Managed tool installation (no manual installs)
**Decision:** A Tool Management subsystem (Registry/Provider/Manager/Executor)
downloads pinned, checksum-verified binaries into a managed dir. Git stays light.
**Why:** Reproducibility and zero manual setup. New tools = one registry entry.
See `TOOLCHAIN.md`.

### ADR-004 — Pinned tool versions, verify against official checksums
**Decision:** Pin latest-stable PD versions (subfinder 2.14.0, httpx 1.9.0, katana
1.6.1). Verify downloads against the release's official `*_checksums.txt`; allow
optional repo-pinned `sha256` for strict reproducibility.
**Why:** Integrity without fabricating hashes. `setup` prints the observed hash so
it can be pinned later.

### ADR-005 — FastAPI + PostgreSQL + Next.js
**Decision:** Backend FastAPI (Python 3.11+), DB PostgreSQL, frontend Next.js 14
App Router + TS + Tailwind + shadcn/ui.
**Why:** Mature, productive stack; Python aligns with the security ecosystem.

### ADR-006 — Synchronous SQLAlchemy (not async)
**Decision:** Sync SQLAlchemy 2.0 + sessions; endpoints/background run in threads.
**Why:** Recon shells out to blocking subprocesses; sync is simpler and correct.
Async ceremony around blocking I/O would add complexity for no gain.

### ADR-007 — psycopg v3 driver required
**Decision:** `HUNTERAI_DATABASE_URL` must be `postgresql+psycopg://...`; a
validator rejects bare `postgresql://`.
**Why:** Avoid silent psycopg2 fallback; one explicit, modern driver.

### ADR-008 — Background execution via FastAPI BackgroundTasks behind a port
**Decision:** `POST /scans` returns 202 immediately; recon+scan run in a
BackgroundTask. The `ScanRunner` port abstracts the backend.
**Why:** Real scans take minutes; non-blocking API + polling. No Redis/Celery yet —
but the port lets us swap to a queue later without changing the API contract.

### ADR-009 — Completion only after the full run; single DB write
**Decision:** A scan is marked COMPLETED only after recon **and** scanning finish;
results persisted in one `update`.
**Why:** The frontend stops polling at a terminal status. Marking COMPLETED early
would make it miss findings produced afterward.

### ADR-010 — Relational results (child tables), not JSON blobs
**Decision:** `subdomains`, `http_services`, `endpoints`, `findings` are child
tables with cascade delete; list-y fields (technologies, references, metadata) are
JSON columns.
**Why:** Queryable for UI/reporting; identity & indexing (severity/plugin).

### ADR-011 — Plugin-based scanner engine with dependency inversion
**Decision:** `ScannerPlugin` Protocol in domain; `ScannerEngine` depends only on
it; plugins discovered via `@register_plugin` + package import.
**Why:** Add a vulnerability check as one new file, zero edits to engine/existing
plugins. Engine isolates per-plugin failures.

### ADR-012 — Ship the framework before content
**Decision:** Sprint 1 M1 built the engine with **no** plugins; M2 integrated it;
M3 adds real plugins.
**Why:** Mirrors Sprint 0 ("plumbing before content"). Plugins need somewhere to
run/persist first. Keeps milestones small and reviewable.

### ADR-013 — Findings stored in column `meta` (not `metadata`)
**Decision:** The domain `Finding.metadata` maps to ORM column `meta`.
**Why:** `metadata` is reserved on SQLAlchemy declarative models.

### ADR-014 — No AI in early sprints; supervised autonomy later
**Decision:** Defer all AI/agents. When added, keep human-in-the-loop and build a
non-bypassable scope/execution guard first.
**Why:** Trust, safety, and legality. Automate the tedious surface first; AI is a
force multiplier, not an autonomous hunter (yet). See `AGENTS_FUTURE.md`.
