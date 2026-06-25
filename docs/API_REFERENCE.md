# API_REFERENCE

FastAPI service. Base URL `http://127.0.0.1:8000`; versioned routes under
`/api/v1`. Interactive docs at `/docs`. CORS allows `http://localhost:3000` by
default (`HUNTERAI_CORS_ORIGINS`).

Source: `backend/app/interfaces/api/`. Schemas: `schemas/scan.py`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness (also `/api/v1/health`) |
| GET | `/api/v1/tools` | Required vs installed tool status |
| POST | `/api/v1/scans` | Create scan; start recon+scan in background; **202** |
| GET | `/api/v1/scans` | List recent scans (summaries) |
| GET | `/api/v1/scans/{id}` | Scan status + results (poll this) |

### GET /health
```json
{ "status": "ok", "app": "HunterAI", "version": "0.0.0", "env": "development" }
```

### GET /api/v1/tools
```json
[ { "name":"subfinder","required_version":"2.14.0","installed":true,
    "installed_version":"2.14.0","needs_install":false }, ... ]
```

### POST /api/v1/scans
Request:
```json
{ "domain": "example.com" }
```
Response `202`:
```json
{ "scan_id":"<uuid>", "status":"running",
  "target_domain":"example.com", "created_at":"<iso8601>" }
```
- Domain is normalized (scheme/port/path stripped, lowercased, validated).
- Invalid domain → `422` with the validation message.

### GET /api/v1/scans
```json
[ { "scan_id":"<uuid>", "target_domain":"example.com", "status":"completed",
    "counts": {"subdomains":3,"services":2,"endpoints":10,"findings":0},
    "created_at":"...", "finished_at":"..." } ]
```

### GET /api/v1/scans/{id}
`200` (poll until `status` ∈ {completed, failed}):
```json
{
  "scan_id":"<uuid>", "target_domain":"example.com", "status":"completed",
  "counts": {"subdomains":3,"services":2,"endpoints":10,"findings":0},
  "created_at":"...", "started_at":"...", "finished_at":"...", "error": null,
  "subdomains": [ {"host":"api.example.com","source":"subfinder"} ],
  "services": [ {"url":"https://example.com","status_code":200,"title":"...",
                 "webserver":"nginx","content_length":1256,"host":"...",
                 "technologies":["nginx"],"input":"example.com"} ],
  "endpoints": [ {"url":"https://example.com/login","method":"GET","source":"katana"} ],
  "findings": [ {"id":"<uuid>","plugin":"security-headers","name":"Missing CSP",
                 "severity":"medium","target":"https://example.com",
                 "description":"...","confidence":"high","evidence":"...",
                 "references":["..."],"metadata":{"header":"content-security-policy"}} ]
}
```
- `404` if the scan id is unknown.
- `findings` is **empty until scanner plugins are added (Sprint 1 M3)**.
- `severity` ∈ `info|low|medium|high|critical`; `confidence` ∈ `low|medium|high`.

## Scan lifecycle
```
POST /scans → 202 (status: running, persisted immediately)
   background: recon (subfinder→httpx→katana) → scanner engine → persist results
GET /scans/{id} (every ~2s) → status running → completed|failed
```
A scan reaches `completed` only after **both** recon and scanning finish (ADR-009).

## Execution model
Recon+scan run via FastAPI BackgroundTasks behind the `ScanRunner` port
(`application/ports.py`). Composition root: `infrastructure/execution/execute_scan`.
Swappable to Celery/RQ later without changing this contract (ADR-008).

## Adding an endpoint (checklist)
1. Route module under `interfaces/api/routes/`, include it in `router.py`.
2. Request/response models in `interfaces/api/schemas/`.
3. Dependencies via `interfaces/api/deps.py` (repos, use cases).
4. Test under `tests/` (TestClient + SQLite override pattern — see
   `tests/test_api_scans.py`).
5. Update this file.
