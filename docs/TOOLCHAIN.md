# TOOLCHAIN

How HunterAI manages external security tools, and the dev toolchain.

Detailed subsystem doc: `docs/TOOLS.md`. This file is the canonical overview.

## Managed security tools

Users never install tools by hand. The **Tool Management subsystem**
(`backend/app/infrastructure/tools/`) downloads pinned, checksum-verified binaries
into a managed directory.

Four pillars:
| Pillar | File | Role |
|--------|------|------|
| Registry | `registry.py` | Declarative catalog; pinned versions; per-platform sources |
| Provider | `provider.py` | Download → verify SHA-256 → extract binary |
| Manager | `manager.py` | discover / install / update / status / resolve / run |
| Executor | `executor.py` | Run a binary (no shell, timeout, captured output) |

Ports: `app/domain/ports/tools.py` (`ToolManagerPort`, `ToolExecutorPort`). The
recon adapters depend on the port, not the concrete manager.

### Pinned tools (Sprint 0/1)
| Tool | Version | Purpose |
|------|---------|---------|
| subfinder | 2.14.0 | passive subdomain enumeration |
| httpx | 1.9.0 | HTTP probing / live-host detection |
| katana | 1.6.1 | crawling / endpoint discovery |

Source: ProjectDiscovery GitHub releases (`linux/amd64`, `linux/arm64`). Bump
versions in the constants at the top of `registry.py`.

### Integrity model
- If a source pins `sha256`, it is strictly enforced.
- Otherwise the asset is verified against the release's official
  `*_checksums.txt`, and `setup` prints the observed hash to pin later (ADR-004).

### Install layout (managed dir, git-ignored)
```
<tools_dir>/<name>/<name>        # executable
<tools_dir>/<name>/.meta.json    # {name, version, sha256, source_url, installed_at}
```
`tools_dir` defaults to `<repo>/.hunterai/tools` (override `HUNTERAI_TOOLS_DIR`).

### CLI
```bash
python -m app.tools_cli status          # required vs installed
python -m app.tools_cli setup           # install all
python -m app.tools_cli setup --force   # reinstall + re-verify
python -m app.tools_cli install httpx
python -m app.tools_cli paths
```

### Adding a tool (e.g. Nuclei, ffuf, Naabu)
One `ToolSpec` entry in `registry.py` (PD tools reuse the `_pd_sources` helper).
No other changes for install/execution; a recon/scanner adapter consumes it.

## Dev toolchain

- **Python** 3.11+ (backend). Deps in `backend/pyproject.toml`:
  fastapi, uvicorn, pydantic(+settings), SQLAlchemy 2.0, psycopg[binary] v3,
  alembic. Dev extras: pytest, pytest-asyncio, httpx, ruff, mypy.
- **Node** 20+/22 (frontend). Next.js 14, React 18, TypeScript 5, Tailwind 3,
  shadcn/ui (radix-slot, cva, clsx, tailwind-merge, lucide-react).
- **Lint/type:** `ruff` (line length 100), `mypy --strict` (backend);
  `tsc --noEmit` + `eslint-config-next` (frontend).
- **Tests:** `pytest -q` (backend, 56 passing); frontend validated via
  `npm run typecheck` + `npm run build`.

### Per-subsystem CLIs
| CLI | Purpose |
|-----|---------|
| `python -m app.tools_cli` | manage security tools |
| `python -m app.recon_cli example.com` | run recon end-to-end (dev) |
| `python -m app.scanner_cli list` | list scanner plugins |
| `python -m app.db_cli init\|drop` | create/drop tables (dev shortcut) |

### Environment variables (prefix `HUNTERAI_`)
| Var | Default | Notes |
|-----|---------|-------|
| `HUNTERAI_ENV` | development | |
| `HUNTERAI_DEBUG` | true | |
| `HUNTERAI_API_V1_PREFIX` | /api/v1 | |
| `HUNTERAI_CORS_ORIGINS` | http://localhost:3000 | comma-separated allowed |
| `HUNTERAI_TOOLS_DIR` | `<repo>/.hunterai/tools` | managed tools dir |
| `HUNTERAI_DATABASE_URL` | (none) | must be `postgresql+psycopg://...` |

Frontend: `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).
