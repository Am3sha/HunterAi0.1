# DATABASE

PostgreSQL in production; SQLite (in-memory, `StaticPool`) in tests. ORM is
SQLAlchemy 2.0 (sync). Models use DB-agnostic types (`Uuid`, `JSON`) so the same
schema runs on both.

- Models: `backend/app/infrastructure/persistence/models.py`
- Mapping: `backend/app/infrastructure/persistence/repositories.py`
- Engine/session: `backend/app/infrastructure/persistence/database.py`
- Migrations: `backend/alembic/versions/` (`0001_initial`, `0002_findings`)

Connection: `HUNTERAI_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`
(psycopg v3 scheme required — see ADR-007).

## Schema

```
targets
  id            UUID  PK
  domain        str(253)  (index)
  created_at    datetime(tz)

scans
  id            UUID  PK
  target_id     UUID  FK→targets.id (index)
  target_domain str(253)
  status        str(20)  (index)   pending|running|completed|failed
  error         text  null
  created_at    datetime(tz)
  started_at    datetime(tz) null
  finished_at   datetime(tz) null

subdomains
  id        int PK autoincrement
  scan_id   UUID FK→scans.id (index)
  host      str(253)
  source    str(64) null

http_services
  id             int PK
  scan_id        UUID FK→scans.id (index)
  url            text
  input          str(253) null
  status_code    int null
  title          text null
  webserver      str(255) null
  content_length int null
  host           str(255) null
  technologies   JSON          (list[str])

endpoints
  id        int PK
  scan_id   UUID FK→scans.id (index)
  url       text
  method    str(16) null
  source    str(64) null

findings                      ← added in 0002 (Sprint 1 M2); extended in 0003 (Sprint 2 M2)
  id              int PK
  scan_id         UUID FK→scans.id (index)
  uid             UUID            (domain Finding.id; stable identity)
  plugin          str(64)  (index)
  name            text
  severity        str(16)  (index)   info|low|medium|high|critical
  target          text
  description     text  default ''
  confidence      str(16)            low|medium|high
  evidence        text null
  references      JSON  (list[str])
  meta            JSON  (dict[str,str])   ← domain Finding.metadata (col renamed; ADR-013)
  cvss_version    str(16)  null
  cvss_vector     text null
  cvss_base_score float    null
  cwe_ids         JSON  (list[str])
  owasp_categories JSON  (list[str])
  remediation     text null
```

Relationships: `scans` → `subdomains` / `http_services` / `endpoints` / `findings`
are one-to-many with `cascade="all, delete-orphan"` and `lazy="selectin"`.
`repositories._apply_results` **replaces** a scan's child rows on update (recon then
scan results are written in the final `update`).

## Migrations

```bash
cd backend
alembic upgrade head                 # apply all
alembic revision -m "description"     # new migration (then hand-edit; autogenerate
                                      # is not wired — env.py loads metadata but we
                                      # write explicit ops)
# dev shortcut (no Alembic):
python -m app.db_cli init            # create_all
python -m app.db_cli drop            # drop_all
```

`alembic/env.py` injects `HUNTERAI_DATABASE_URL` from settings and targets
`Base.metadata`.

## Adding a table/field (checklist)
1. Edit `models.py`.
2. Update `repositories.py` mapping (`_apply_results` and `_to_domain`).
3. Add a migration in `alembic/versions/` (set `down_revision`).
4. Update API schema if exposed (`interfaces/api/schemas/`).
5. Update/extend tests (`tests/test_persistence.py`, `tests/test_api_scans.py`).
6. Update `DATABASE.md` + `API_REFERENCE.md`.
