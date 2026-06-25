# HunterAI Backend

FastAPI service built with **Clean Architecture**.

## Layers

| Package           | Responsibility                                              | May import |
|-------------------|-------------------------------------------------------------|------------|
| `app.domain`      | Entities + ports (interfaces). Pure Python.                 | nothing internal |
| `app.application` | Use cases / orchestration.                                  | `domain` |
| `app.infrastructure` | Tool Manager, persistence, subprocess execution.         | `domain`, `application` |
| `app.interfaces`  | Delivery layer: FastAPI routers + schemas.                  | all |
| `app.core`        | Cross-cutting: config, logging, DI wiring.                  | all |

**Dependency rule:** inner layers never import outer ones.

## Run (inside WSL / Linux)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Database (Postgres). Optionally start one with Docker from the repo root:
#   docker compose up -d
alembic upgrade head            # create schema (or: python -m app.db_cli init)

# Install the security tools (subfinder/httpx/katana):
python -m app.tools_cli setup

uvicorn app.main:app --reload
# → http://127.0.0.1:8000/health
# → http://127.0.0.1:8000/docs
```

See [`../docs/API.md`](../docs/API.md) for endpoints and the scan lifecycle.
