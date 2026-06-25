# PROJECT_STATE — HunterAI

> **Start here.** This is the single source of truth for "where the project is
> right now." If you are a new session resuming work, read this file top to
> bottom, then `ARCHITECTURE.md` and `ROADMAP.md`.

_Last updated: end of Sprint 1, Milestone 2._

---

## 1. What HunterAI is

An **AI-assisted bug bounty platform for authorized security testing only.** Not a
blind scanner — the long-term goal is an assistant that reasons like a junior
pentester working under a human researcher. The human is always in control.

Currently HunterAI is a **reconnaissance + (framework-stage) vulnerability
scanner**. No AI is implemented yet — that is deliberately deferred.

## 2. Resume Here (TL;DR for a new session)

- **Repo:** `E:\HunterAI` on Windows (editing) = `/mnt/e/HunterAI` in WSL.
  **All builds/tests/runs happen inside WSL/Linux**, never native Windows.
- **Monorepo:** `backend/` (FastAPI, Clean Architecture), `frontend/` (Next.js 14),
  `docs/`.
- **Tests:** 56 passing (backend). There is no committed git history; the working
  tree is the state. Run tests in a venv (see `TOOLCHAIN.md`).
- **Where we are:** Sprint 0 complete (recon MVP). Sprint 1: **M1 done**
  (plugin scanner engine), **M2 done** (engine integrated into the scan pipeline,
  findings persisted + in API). **Next up: Sprint 1 M3 = first real scanner
  plugins.**
- **Important:** the scanner engine ships with **zero plugins**, so a scan
  currently returns `findings: []`. The whole path is proven and waiting for M3.
- **Golden rule:** preserve Clean Architecture boundaries, the existing coding
  style, and the test-first philosophy. Build milestone-by-milestone; stop for
  review after each.

## 3. Current capability (works today)

End-to-end flow, all wired:

```
POST /api/v1/scans {"domain":"example.com"}
  → 202 {scan_id, status:"running"}
  → background: recon (subfinder → httpx → katana) → scanner engine (no plugins) → persist
GET /api/v1/scans/{id}  (frontend polls every 2s)
  → {status, counts, subdomains[], services[], endpoints[], findings[]}
```

- **Tool management:** subfinder/httpx/katana auto-installed (pinned, checksum-
  verified) into a managed dir. `python -m app.tools_cli setup`.
- **Recon pipeline:** subdomain enum → HTTP probe → crawl, persisted.
- **Scanner engine:** plugin framework with registry/discovery; runs after recon;
  isolates per-plugin failures; aggregates `Finding`s. **No real plugins yet.**
- **Persistence:** PostgreSQL (prod) / SQLite (tests); Alembic migrations
  `0001_initial`, `0002_findings`.
- **Frontend:** target input → start scan → poll → display subdomains / services /
  endpoints. **Does not display findings yet** (deferred to M4).

## 4. What is NOT implemented (explicitly out, so far)

| Area | Status |
|------|--------|
| AI / LLM / agents | Not started (future; see `AGENTS_FUTURE.md`) |
| Real vulnerability plugins | **Next milestone (M3)** — none exist yet |
| Frontend findings display | Deferred to Sprint 1 M4 |
| Report generation | Not started |
| Authentication / multi-user | Not started |
| Memory / knowledge base | Planned (see `KNOWLEDGE_BASE_PLAN.md`) |
| Browser automation | Not started |
| Async DB / queue (Celery/Redis) | Not used; sync + FastAPI BackgroundTasks by design |

## 5. Repository map

```
HunterAI/
├── backend/                 FastAPI service (Clean Architecture)
│   ├── app/
│   │   ├── domain/          entities + ports (pure, no framework)
│   │   ├── application/     use cases (orchestration)
│   │   ├── infrastructure/  tools, recon, scanner, persistence, execution
│   │   ├── interfaces/api/  FastAPI routers + schemas
│   │   ├── core/            config, logging
│   │   ├── main.py          app factory
│   │   └── *_cli.py         tools_cli, recon_cli, scanner_cli, db_cli
│   ├── alembic/             migrations (0001_initial, 0002_findings)
│   └── tests/               56 tests
├── frontend/                Next.js 14 App Router + TS + Tailwind + shadcn/ui
├── docs/                    ← you are here
└── docker-compose.yml       optional local Postgres
```

Full layer detail: `ARCHITECTURE.md`. File-by-file index also there.

## 6. How to run (WSL)

```bash
# Backend
cd /mnt/e/HunterAI/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d            # or point HUNTERAI_DATABASE_URL at a Postgres
alembic upgrade head
python -m app.tools_cli setup   # install subfinder/httpx/katana
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs

# Frontend (another shell)
cd /mnt/e/HunterAI/frontend
cp .env.local.example .env.local
npm install && npm run dev      # http://localhost:3000

# Tests
cd backend && pytest -q         # 56 passing
```

## 7. Known caveats / gotchas

- **psycopg v3 only:** `HUNTERAI_DATABASE_URL` must be `postgresql+psycopg://...`
  (a validator rejects bare `postgresql://`).
- **Run in WSL:** the tool manager fetches `linux/amd64|arm64` binaries; native
  Windows execution is unsupported by design.
- **SQLAlchemy reserved name:** the findings `metadata` field is stored in a column
  named `meta` (declarative `metadata` is reserved).
- **Counts dict** now includes a `findings` key — any new assertion on `scan.counts`
  must include it.
- **No git repo** is initialized; there is no commit history to diff against.

## 8. Immediate next step

**Sprint 1, Milestone 3 — first real scanner plugins.** Each plugin is one new
file under `backend/app/infrastructure/scanner/plugins/`, decorated with
`@register_plugin`; no existing code changes. See `PLUGIN_DEVELOPMENT.md` and
`SPRINT_1_PLAN.md`.
