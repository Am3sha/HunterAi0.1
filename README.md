# HunterAI

AI-assisted bug bounty platform for **authorized security testing only**.

HunterAI is **not** a traditional vulnerability scanner. The long-term goal is an
intelligent assistant that helps security researchers perform reconnaissance,
analyze attack surfaces, plan testing strategies, collect evidence, and validate
findings — with the human researcher always in control.

> ⚠️ **Authorized use only.** Only run HunterAI against targets you own or are
> explicitly permitted to test (e.g. an in-scope bug bounty program). You are
> responsible for staying within the rules of engagement of the target program.

---

## Status — Sprint 0 (Reconnaissance MVP)

No AI. No browser automation. No reporting. No memory. No authentication.
A clean, extensible recon pipeline:

```
Target  →  Subfinder (subdomains)  →  httpx (live hosts)  →  Katana (endpoints)  →  Results
```

Security tools are **not** installed by hand. A built-in Tool Management system
downloads, verifies, and runs them into a managed tools directory.

See [`docs/SPRINT0.md`](docs/SPRINT0.md) for the milestone plan.

---

## Architecture

- **Clean Architecture** — domain logic independent of frameworks, DB, and I/O.
- **Modular** — new tools are added via the Tool Registry without touching the core.
- **Linux-first** — Ubuntu / Kali are primary. Windows users should use **WSL**.
- **Docker optional** — not the default execution environment.

```
HunterAI/
├── backend/     FastAPI service (Clean Architecture)
├── frontend/    Next.js UI
└── docs/        Architecture & sprint docs
```

## Tech stack

| Layer    | Choice                          |
|----------|---------------------------------|
| Frontend | Next.js                         |
| Backend  | FastAPI (Python 3.11+)          |
| Database | PostgreSQL                      |
| Tools    | Subfinder, httpx, Katana (managed) |

## Getting started

> Run everything below **inside WSL / Linux**, not Windows Git Bash.

```bash
# backend (API)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head             # create schema (docker compose up -d for a local Postgres)
python -m app.tools_cli setup    # install subfinder / httpx / katana
uvicorn app.main:app --reload    # http://127.0.0.1:8000/health

# frontend (UI) — in another shell
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                      # http://localhost:3000
```

See [`docs/API.md`](docs/API.md) for the API and [`docs/TOOLS.md`](docs/TOOLS.md)
for tool management.
