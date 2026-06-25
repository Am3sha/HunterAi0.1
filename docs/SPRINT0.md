# Sprint 0 — Reconnaissance MVP

**Goal:** a clean, extensible recon pipeline. No AI, no browser automation, no
reporting, no memory, no authentication.

## Flow

```
Input target → Start scan → Subfinder → httpx → Katana → Save results → Display
```

## Out of scope (Sprint 0)

AI · browser automation · reporting · memory · authentication.

## Milestones

| #  | Milestone                                   | Outcome |
|----|---------------------------------------------|---------|
| M1 | Repo scaffold + Clean Architecture skeleton | Backend boots `/health`; layered packages in place |
| M2 | Tool Management subsystem + setup installer  | Registry / Provider / Manager / Executor; tools auto-installed w/ checksum verify |
| M3 | Domain + recon pipeline use case            | Target/Scan entities; Subfinder→httpx→Katana orchestration; parsers |
| M4 | Persistence + API                           | PostgreSQL + repositories; create-target / start-scan / get-results endpoints |
| M5 | Next.js frontend                            | Target input, start scan, results display, wired to API |

## Architecture decisions (locked)

- Clean Architecture, modular design.
- Linux-first (Ubuntu / Kali); Windows → WSL.
- Docker optional, not default.
- Monorepo: `/backend` + `/frontend`.
- Tools acquired as **pinned GitHub-release binaries**, checksum-verified, placed
  in a managed tools directory (kept out of git).
- Runtime target for Sprint 0: **linux/amd64**.

## Clean Architecture layers (backend)

```
domain/         Entities + ports (interfaces). Pure Python. No framework imports.
application/    Use cases. Depends only on domain.
infrastructure/ Implementations: tools, persistence, external processes.
interfaces/     Delivery: FastAPI routers + schemas. Wires everything together.
core/           Cross-cutting: config, logging, DI.
```

**Dependency rule:** `domain ← application ← infrastructure / interfaces`.
Inner layers never import outer layers.
