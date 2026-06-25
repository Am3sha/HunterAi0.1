# KNOWLEDGE_BASE_PLAN

A forward-looking plan for HunterAI's memory/knowledge layer. **Not implemented
yet** — this records intent so it can be built coherently later. No code today.

## Why
A real bug hunter accumulates knowledge: what a target runs, what's been tried,
which leads paid off. To behave like a junior pentester (the long-term vision),
HunterAI needs persistent, queryable memory — so attempt N+1 is smarter than
attempt N, and so future AI agents have grounded context rather than re-deriving
everything each run.

## Scope (what the KB should hold)
1. **Target knowledge** — per target/domain: technologies, infrastructure,
   observed behaviors, auth model, notable endpoints. Accumulated across scans.
2. **Attempt history** — what was run (tools, plugins, params) and the outcome, so
   work isn't blindly repeated and coverage is visible.
3. **Findings ledger** — confirmed/likely issues over time, with status and
   dedup across scans (today `findings` are per-scan only).
4. **Evidence** — request/response/screenshots linked to findings for
   reproducibility (ties into a future reporting sprint).
5. **Reference knowledge** — reusable detection knowledge (payload sets, check
   definitions, references) decoupled from any single target.

## Design principles
- **Clean Architecture:** a `KnowledgeRepository` port in `domain/ports/`, with a
  SQLAlchemy implementation in `infrastructure/persistence/`. Use cases depend on
  the port. Mirrors how scans/targets are stored today.
- **Inspectable, not magic:** explicit records and queries, not opaque embeddings
  (vector search can be an *additional* index later, not the source of truth).
- **Append-only where it aids audit:** attempt history and evidence are
  immutable events; derived views (current target profile) are computed/rolled up.
- **Incremental:** start by promoting today's per-scan results into durable,
  cross-scan, per-target knowledge.

## Likely data shape (sketch — subject to change)
```
target_profile   (target_id, technologies, infra, auth_model, updated_at, ...)
attempt          (id, target_id, scan_id, kind, params JSON, outcome, at)   [append-only]
finding_ledger   (id, target_id, fingerprint, severity, status, first_seen, last_seen)
evidence         (id, finding_id|attempt_id, type, ref/blob, at)            [append-only]
knowledge_item   (id, category, name, payload JSON)   # reusable, target-agnostic
```
`fingerprint` enables dedup of the same issue across scans (e.g. hash of
plugin+target+key metadata).

## Phasing (tentative, post Sprint 1)
1. **KB-1 Persistence skeleton** — ports + tables + repository; no behavior change.
2. **KB-2 Promote findings** — write a cross-scan findings ledger with dedup.
3. **KB-3 Target profiles** — roll recon/scan results into a per-target profile.
4. **KB-4 Attempt history** — record what ran; expose "already tried" to the UI.
5. **KB-5 Evidence** — capture/store evidence; link to findings (with reporting).
6. **KB-6 AI grounding** — expose the KB to agents as read context / tools
   (depends on `AGENTS_FUTURE.md`).

## Explicitly out of scope now
No implementation, no schema migrations, no AI. This file is a plan only; revisit
before starting KB-1.
