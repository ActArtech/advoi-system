# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## Memory retain (ADR-026)

- All production retains go through `MemoryRouter.retain(MemoryEventType, …)`; routing is `EVENT_WRITE_MAP` in `advoi/memory/write_targets.py`.
- Do not call `retain_strategic` / `aretain` outside `advoi/memory/{router,hindsight,bridge_server}.py` (plus Hermes bridge scripts).
- Do not call `retain_operational_unified` from outside `advoi/memory/` — use the router with a mapped event (e.g. `WORKFLOW_EVOLUTION`, `SQUAD_LESSON`).
- Never put fleet backlog text into Hindsight / strategic event types. Fleet-scout tick summaries are operational (`SQUAD_LESSON`) only.
- Guard: `tests/test_memory_retain_audit.py`. Latest inventory: `data/feedback-evidence/advoi-memory-retain-audit-01/audit.md`.

## Brief Curator (ADR-026)

- **Postgres** `decision_briefs` is the only canonical store for open briefs (`EVENT_WRITE_MAP[decision_brief] = postgres`).
- **Redis** `advoi:briefs:open` is cache only: fill-on-read from PG, invalidate-on-write in `upsert_open_brief` (`advoi/memory/briefs_cache.py`).
- **Hindsight** is optional enrich when PG+cache are empty — never merged as a third title source with PG/Redis.
- Seed: `scripts/seed-advoi-briefs.sh` writes PG first; Hindsight seed uses `portfolio_fact` (not `decision_brief`).
- T0 tests: `tests/test_brief_curator_canonical.py`.

## Ingestion lifecycle (M7.2–M7.3 / moat R4)

- Happy path: `uploaded → triaged → needs_review → approved → dispatched` (`advoi/ingestion/lifecycle.py`).
- Upload stays `uploaded` only; never auto-dispatch on upload.
- `dispatch_item_dev` requires status `approved` (API returns 409 otherwise).
- T0: `tests/test_ingestion_lifecycle.py`.

## Portfolio Event Log (PEL / moat R1)

- **Authority:** append-only Postgres `portfolio_events` is the single control-plane event log. Deprecate `memory_events` after idempotent backfill (do not keep dual long-term authority).
- **Schema design:** `docs/architecture/07-portfolio-event-log.md` — fields `{ id, timestamp, venture_id, source, type, payload, guardian_status, execution_ref, trace_id }`.
- **Migration plan:** `data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md` — backfill via `legacy_memory_event_id` UNIQUE + `ON CONFLICT DO NOTHING`.
- **Runtime today:** writers still use `memory_events` via `retain_structured` until ship `advoi-analytics-pel-schema-01`.
- **Minimum emit points (implementation):** frame run (`run_frame`), fleet trigger (`invoke_fleet_trigger` / confirmation), voice intent (not every Redis `VOICE_TURN`).
- **ADR-026:** PEL is the Postgres structured-event surface; not a live double-write into Hindsight. No fleet backlog body in event payloads as strategic content.
