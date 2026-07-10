# Portfolio Event Log (PEL)

**Status:** Implemented (schema + minimum emit points)  
**Ship:** `advoi-data-memory-events-pel-01` (design) · `advoi-analytics-pel-schema-01` (runtime)  
**Code:** `advoi/analytics/pel.py` · `deploy/migrations/001_portfolio_events.sql` · `tests/test_portfolio_events.py`  
**Authority:** [PORTFOLIO-SYSTEM-MOAT.md §7.1 / R1](../reviews/PORTFOLIO-SYSTEM-MOAT.md) · [ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md) · ADR-026

---

## 1. Why PEL exists

Competitors can copy a voice UI. They cannot copy **years of typed portfolio events** tied to ventures, bets, gates, and outcomes.

Moat R1 defines a single control-plane primitive: an append-only **Portfolio Event Log** in ADVoi Postgres. Hindsight may receive **nightly synthesis**, not per-event double-write.

Today Postgres has a thinner sibling:

| Table | Columns (today) | Consumers |
|-------|-----------------|-----------|
| `memory_events` | `id`, `event_type`, `payload`, `created_at` | None exposed; written via `retain_structured` |

That table overlaps the planned PEL and creates dual-authority risk (see data-memory review: *memory_events ≠ PEL*).

**Target:** one append-only table — `portfolio_events` — is the system of record for executive/control-plane events. `memory_events` is migrated then deprecated.

---

## 2. PortfolioEvent schema

Logical record (moat §7.1):

```text
PortfolioEvent {
  id, timestamp, venture_id, source, type,
  payload, guardian_status, execution_ref, trace_id
}
```

### 2.1 Column contract

| Field | SQL type (proposed) | Required | Description |
|-------|---------------------|----------|-------------|
| `id` | `UUID` PK default `gen_random_uuid()` | yes | Stable event id (new writes). Migrated rows may preserve legacy bigint via `legacy_memory_event_id`. |
| `timestamp` | `TIMESTAMPTZ` NOT NULL default `NOW()` | yes | Event time (use source clock when known; else insert time). |
| `venture_id` | `TEXT` NOT NULL | yes | Portfolio venture slug (`clapart`, `advoi`, …). Use `unknown` only when unresolvable. |
| `source` | `TEXT` NOT NULL | yes | Origin module. Controlled vocabulary (below). |
| `type` | `TEXT` NOT NULL | yes | Event class. Controlled vocabulary (below). |
| `payload` | `JSONB` NOT NULL default `{}` | yes | Structured body; no fleet backlog dumps into strategic synthesis. |
| `guardian_status` | `TEXT` NULL | no | Gate outcome when applicable: `not_required` \| `pending` \| `allowed` \| `denied` \| `error`. |
| `execution_ref` | `TEXT` NULL | no | Link to external work: fleet job id, ingest item id, squad dispatch id, GitHub run, etc. |
| `trace_id` | `TEXT` NULL | no | OTel / request correlation id when observability is on. |
| `legacy_memory_event_id` | `BIGINT` NULL UNIQUE | no | Migration-only back-pointer to `memory_events.id` (idempotency key). |
| `created_at` | `TIMESTAMPTZ` NOT NULL default `NOW()` | yes | Insert time (may differ from `timestamp`). |

Indexes (proposed):

- `(venture_id, timestamp DESC)` — venture timeline
- `(source, type, timestamp DESC)` — analytics filters
- `(trace_id)` WHERE NOT NULL — trace join
- `(execution_ref)` WHERE NOT NULL — side-effect join
- UNIQUE `(legacy_memory_event_id)` WHERE NOT NULL — idempotent migration

### 2.2 Controlled vocabularies

**`source`** (moat + analytics emit set):

| Value | Meaning |
|-------|---------|
| `voice` | LiveKit / Pipecat path, voice operators |
| `ingest` | Document ingestion vertical |
| `fleet` | fm-bridge / FirstMate trigger path |
| `paperclip` | Future Paperclip approvals |
| `aether` | Post-frame Aether / portfolio enrich |
| `api` | HTTP frame run / operators without voice |
| `daemon` | Agent daemon tick / bootstrap |
| `squad` | Squad dispatch bridge |
| `guardian` | Gate / recovery / notification |
| `memory` | Structured retain mirror (legacy `memory_events` rows) |
| `system` | Migrations, seeds, ops |

**`type`** (moat classes + concrete subtypes):

| Class (moat) | Example concrete `type` values |
|--------------|--------------------------------|
| `attention` | `frame_run`, `voice_intent`, `systems_pulse` |
| `decision` | `governance_decision`, `decision_brief`, `review_queued` |
| `dispatch` | `fleet_trigger`, `squad_dispatch`, `ingest_dispatched` |
| `memory` | `portfolio_fact`, `squad_lesson`, `project_state`, `master_state` |
| `gate` | `guardian_gate`, `confirmation_required`, `confirmation_resolved` |

Concrete types should stay snake_case and stable; analytics ships group by class via prefix or a later `type_class` generated column if needed.

### 2.3 Module usage (moat map)

| Module | Uses PEL for |
|--------|----------------|
| voice | Intent + frame outcomes; not every Redis voice turn |
| ingestion | Lifecycle transitions (uploaded → … → dispatched) |
| guardian | Gate decisions on consequential writes |
| fleet | Mirror bridge invocations (read-back) |
| aether | Gate / belief side-effects after frames |
| observability | Link `trace_id` to spans |
| reporting | BI layer (`advoi-analytics-pel-schema-01`+) |

---

## 3. Mapping from existing `memory_events`

### 3.1 Current shape

Created inline in `advoi/memory/postgres_store.py`:

```sql
CREATE TABLE IF NOT EXISTS memory_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Writers: `MemoryRouter.retain` → `WriteTarget.POSTGRES` → `retain_structured(event_type, payload)` for event types mapped to Postgres in `EVENT_WRITE_MAP`:

| `MemoryEventType` | Postgres today? | PEL `type` | Suggested PEL `source` |
|-------------------|-----------------|------------|------------------------|
| `portfolio_fact` | yes (+ Hindsight) | `portfolio_fact` | `memory` (legacy) / caller source when known |
| `governance_decision` | yes (+ Hindsight) | `governance_decision` | `memory` / `guardian` |
| `squad_lesson` | yes (+ Letta) | `squad_lesson` | `aether` / `squad` / `daemon` |
| `decision_brief` | yes | `decision_brief` | `memory` |
| `project_state` | yes | `project_state` | `memory` |
| `master_state` | yes | `master_state` | `memory` |
| others | no Postgres write | n/a | n/a |

### 3.2 Row mapping

| `memory_events` | `portfolio_events` |
|-----------------|--------------------|
| `id` | `legacy_memory_event_id` (preserve); new `id` = UUID |
| `created_at` | `timestamp` and `created_at` |
| `event_type` | `type` (1:1 for known `MemoryEventType` values) |
| `payload` | `payload` (pass-through JSONB) |
| *(missing)* | `venture_id` = `COALESCE(payload->>'venture_id', payload->>'project', 'unknown')` |
| *(missing)* | `source` = `'memory'` for backfill (emit path will set real source later) |
| *(missing)* | `guardian_status` = `payload->>'guardian_status'` if present else NULL |
| *(missing)* | `execution_ref` = `COALESCE(payload->>'execution_ref', payload->>'job_id', payload->>'dispatch_id')` |
| *(missing)* | `trace_id` = `payload->>'trace_id'` if present else NULL |

### 3.3 What does **not** migrate into PEL

| Store | Reason |
|-------|--------|
| Redis `VOICE_TURN` / rolling summary | Ephemeral; high volume; not audit moat |
| Hindsight beliefs | Synthesis tier; optional nightly export **from** PEL, not dual live write |
| Guardian JSONL free-form | Keep file log; emit structured `gate` rows into PEL at gate call sites |
| Fleet backlog files | File authority for queue text; PEL stores **actions**, not backlog body |

ADR-026 write targets remain: PEL is the **Postgres structured event** surface, not a replacement for Hindsight/Letta/Redis.

---

## 4. Emit points (for analytics ship)

Minimum viable producers for `advoi-analytics-pel-schema-01` and moat R1 validation (“every bridge invoke creates an event row”):

### 4.1 Frame run

| Item | Detail |
|------|--------|
| **Where** | End of `advoi/routing/frame_runner.py::run_frame` after `FrameResult` is built (and after `post_frame_aether` or alongside it) |
| **Also** | API paths that call `run_frame` / `run_frames_parallel` inherit this single choke point |
| **source** | `api` if HTTP-origin; prefer explicit `source` arg later; default `daemon` for agent ticks |
| **type** | `frame_run` |
| **payload** | `{ frame_id, agent_id, status, spoken_summary_len, confirmed, refresh, detail_keys… }` — avoid dumping full spoken text if PII-sensitive; store hash/length + key detail fields |
| **venture_id** | From execution context / portfolio registry when available; else frame detail / `advoi` |
| **guardian_status** | `allowed` / `pending` / `not_required` from confirmation frames |
| **execution_ref** | Optional: cache key or review-queue item id |
| **trace_id** | From OTel context when enabled |

### 4.2 Fleet trigger

| Item | Detail |
|------|--------|
| **Where** | `advoi/fleet/trigger.py` after `invoke_fleet_trigger` returns; and/or immediately after `evaluate_fleet_confirmation` resolves allow/deny |
| **source** | `fleet` (caller may be voice/API; record `payload.caller` = `voice`\|`api`) |
| **type** | `fleet_trigger` on invoke; `guardian_gate` on confirmation evaluation |
| **payload** | `{ action, project, mock, status, exit_code, output_excerpt }` — **not** full fleet backlog |
| **guardian_status** | From `evaluate_fleet_confirmation` |
| **execution_ref** | Bridge run id / message id if available |
| **venture_id** | Fleet project slug |

### 4.3 Voice intent

| Item | Detail |
|------|--------|
| **Where** | After intent resolution in voice path (`intent_processor` / `respond` / operator catalog) — **not** every Redis `VOICE_TURN` |
| **source** | `voice` |
| **type** | `voice_intent` |
| **payload** | `{ intent_id or frame_id, transcript_hash or short excerpt, route, confirmed }` |
| **guardian_status** | When intent requires confirmation |
| **trace_id** | Session/correlation id |

### 4.4 Recommended phase order

1. **Schema + migrate** `memory_events` → `portfolio_events` (this design; implement in analytics/schema ship).  
2. **Emit:** fleet trigger (highest moat / R1 validation value).  
3. **Emit:** frame_run choke point.  
4. **Emit:** voice_intent (analytics + operator funnels).  
5. Later: ingestion transitions, squad dispatch, guardian recovery as `gate` / `dispatch`.

---

## 5. SQL (applied by analytics ship)

> Canonical file: [`deploy/migrations/001_portfolio_events.sql`](../../deploy/migrations/001_portfolio_events.sql). Runtime also `CREATE TABLE IF NOT EXISTS` on first `append_event` when `DATABASE_URL` is set.

```sql
-- PEL: portfolio_events (append-only authority)
-- Requires pgcrypto or pg13+ for gen_random_uuid(); use uuid-ossp if needed.

CREATE TABLE IF NOT EXISTS portfolio_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    venture_id      TEXT NOT NULL,
    source          TEXT NOT NULL,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    guardian_status TEXT NULL,
    execution_ref   TEXT NULL,
    trace_id        TEXT NULL,
    legacy_memory_event_id BIGINT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT portfolio_events_legacy_memory_event_id_key
        UNIQUE (legacy_memory_event_id)
);

CREATE INDEX IF NOT EXISTS portfolio_events_venture_ts_idx
    ON portfolio_events (venture_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS portfolio_events_source_type_ts_idx
    ON portfolio_events (source, type, timestamp DESC);

CREATE INDEX IF NOT EXISTS portfolio_events_trace_id_idx
    ON portfolio_events (trace_id)
    WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS portfolio_events_execution_ref_idx
    ON portfolio_events (execution_ref)
    WHERE execution_ref IS NOT NULL;

-- Optional CHECK constraints (enable once writers are strict):
-- ALTER TABLE portfolio_events ADD CONSTRAINT portfolio_events_source_check
--   CHECK (source IN (
--     'voice','ingest','fleet','paperclip','aether','api','daemon',
--     'squad','guardian','memory','system'
--   ));

-- Idempotent backfill from memory_events (safe to re-run)
INSERT INTO portfolio_events (
    timestamp,
    venture_id,
    source,
    type,
    payload,
    guardian_status,
    execution_ref,
    trace_id,
    legacy_memory_event_id,
    created_at
)
SELECT
    COALESCE(me.created_at, NOW()),
    COALESCE(
        me.payload->>'venture_id',
        me.payload->>'project',
        'unknown'
    ),
    'memory',
    me.event_type,
    me.payload,
    me.payload->>'guardian_status',
    COALESCE(
        me.payload->>'execution_ref',
        me.payload->>'job_id',
        me.payload->>'dispatch_id'
    ),
    me.payload->>'trace_id',
    me.id,
    COALESCE(me.created_at, NOW())
FROM memory_events me
ON CONFLICT (legacy_memory_event_id) DO NOTHING;

-- After dual-write cutover + verification (separate migration):
-- DROP TABLE IF EXISTS memory_events;
```

### Dual-write note (implementation)

Until `retain_structured` writes only to `portfolio_events`:

1. Create `portfolio_events`.
2. Backfill once (idempotent).
3. Dual-write `memory_events` + `portfolio_events` with same logical fields (short window).
4. Point readers (none today) and new analytics at `portfolio_events`.
5. Stop writing `memory_events`; drop table after retention confirmation.

Details: [`data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md`](../../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md).

---

## 6. Relationship to ADR-026 memory tiers

| Tier | Store | PEL role |
|------|-------|----------|
| Strategic | Hindsight | Nightly synthesis **from** PEL aggregates — not live double-write |
| Operational | Letta | Unchanged; optional PEL row when squad lesson also hits Postgres |
| Canonical structured | Postgres | **PEL is the event authority**; `decision_briefs` remains entity table |
| Ephemeral | Redis | No PEL for every turn |
| Failures | Guardian log | Structured gate outcomes also append PEL `type=guardian_gate` |

`MemoryEventType` values that currently target Postgres continue to do so via PEL (`type` = event type string). New control-plane events (`frame_run`, `fleet_trigger`, `voice_intent`) are **not** Hindsight beliefs.

---

## 7. Non-goals (remaining)

- No `/api/events` **query** (GET) endpoint yet (follow-up) — **POST** thin beacon for PWA is implemented (`advoi-analytics-pwa-beacon-01`)
- No BI dashboards yet
- No drop of `memory_events` in this ship (deprecation checklist only)
- No rename of Redis/Guardian stores

### 7.1 PWA thin beacon (`POST /api/events`)

| Item | Detail |
|------|--------|
| **Types** | `pwa_connect`, `frame_tap`, `confirm_shown`, `confirm_accept`, `error` |
| **source** | `api` (HTTP client beacon); payload `client=pwa` |
| **Wire** | `web/components/pwaBeacon.ts` + UI state machine in `VoiceSession` |
| **SDK** | None — first-party fetch only |

---

## 8. Acceptance hooks for implementation ship

See migration plan § “Cross-link: `advoi-analytics-pel-schema-01` acceptance criteria”.

Summary:

- [ ] `portfolio_events` exists on staging Postgres
- [ ] Idempotent migration from `memory_events` verified (row counts + spot checks)
- [ ] Single write path authority: no new orphan `memory_events`-only writers
- [ ] Emit points: frame_run, fleet_trigger, voice_intent produce rows
- [ ] T0 contract: fleet bridge invoke ⇒ ≥1 PEL row
- [ ] Docs: this file + MEMORY-STACK + 04-memory-and-data updated to name PEL

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Initial PEL schema proposal (`advoi-data-memory-events-pel-01`) |
| 2026-07-10 | Runtime: migration + `append_event` + emit points (`advoi-analytics-pel-schema-01`) |
