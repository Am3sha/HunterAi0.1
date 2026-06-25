# API (Sprint 0)

Base URL: `http://127.0.0.1:8000`, versioned routes under `/api/v1`.

## Endpoints

| Method | Path                  | Purpose |
|--------|-----------------------|---------|
| GET    | `/health`             | Liveness (also `/api/v1/health`) |
| GET    | `/api/v1/tools`       | Required vs. installed tool status |
| POST   | `/api/v1/scans`       | Create a scan; start recon in background; returns `202` |
| GET    | `/api/v1/scans`       | List recent scans (summaries) |
| GET    | `/api/v1/scans/{id}`  | Scan status + results (poll this) |

Interactive docs: `http://127.0.0.1:8000/docs`.

## Scan lifecycle

```
POST /api/v1/scans {"domain":"example.com"}
  -> 202 { scan_id, status: "running", target_domain, created_at }

# background: subfinder -> httpx -> katana, results persisted

GET /api/v1/scans/{scan_id}
  -> 200 { status: "running" | "completed" | "failed",
           counts, subdomains[], services[], endpoints[], findings[], error? }
```

`counts` includes `subdomains`, `services`, `endpoints`, and `findings`. Each
finding has: `id`, `plugin`, `name`, `severity` (`info`→`critical`), `target`,
`description`, `confidence`, `evidence`, `references[]`, `metadata{}`.

> A scan runs reconnaissance **then** vulnerability scanning in one background run
> (Sprint 1 M2). Until scanner plugins are added (M3), `findings` is empty.

## Execution model

Recon runs via **FastAPI BackgroundTasks** behind a `ScanRunner` port
(`app/application/ports.py`). No Redis/Celery in Sprint 0. To swap the backend
later (e.g. Celery), implement a new `ScanRunner` that enqueues
`app.infrastructure.execution.execute_scan` — the API contract and use cases stay
the same.

## Example

```bash
curl -s -XPOST localhost:8000/api/v1/scans -H 'content-type: application/json' \
     -d '{"domain":"example.com"}'
# {"scan_id":"...","status":"running","target_domain":"example.com",...}

curl -s localhost:8000/api/v1/scans/<scan_id> | jq '.status, .counts'
```
