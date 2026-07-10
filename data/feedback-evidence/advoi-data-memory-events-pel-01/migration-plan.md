# Migration plan: `memory_events` → PEL `portfolio_events`

**Task:** `advoi-data-memory-events-pel-01` (Architecture ship #5 — moat R1 design)  
**Branch:** `fm/advoi-data-memory-events-pel-01`  
**Scope:** One-table authority decision + idempotent migration design  
**Out of scope:** Applying SQL, runtime emit, dual-write code (implementation: `advoi-analytics-pel-schema-01`)  
**Design doc:** [`docs/architecture/07-portfolio-event-log.md`](../../../docs/architecture/07-portfolio-event-log.md)  
**References:** PORTFOLIO-SYSTEM-MOAT §7.1 / R1 · ARCHITECTURE-DATA-MEMORY-REVIEW · ADR-026 · `advoi/memory/postgres_store.py`

---

## 1. One-table authority decision

### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Dual tables forever** | Keep `memory_events` + add `portfolio_events` | No migration risk | Dual authority; review already flags this as weakest data layer |
| **B. Merge / expand in place** | `ALTER TABLE memory_events` rename + add columns | Single physical table evolution | Awkward rename of `event_type`→`type`, `created_at` semantics; BIGSERIAL vs UUID; harder to dual-run safely |
| **C. New authority + deprecate** *(chosen)* | Create `portfolio_events`; backfill; cut over writers; drop `memory_events` | Clean schema; idempotent backfill key; clear deprecation | Short dual-write window; two tables briefly |

### Decision

**`portfolio_events` is the single authority for control-plane / structured portfolio events.**

- **Deprecate** `memory_events` after verified backfill + writer cutover.
- Do **not** keep dual long-term authority (Option A rejected by ARCHITECTURE-DATA-MEMORY-REVIEW: *“Merge schema into portfolio_events”*).
- Prefer **new table + migrate** (Option C) over in-place ALTER rename (Option B) because:
  1. Moat schema needs UUID + venture/source/type/guardian/execution/trace fields.
  2. `legacy_memory_event_id UNIQUE` gives **idempotent** re-runs.
  3. Zero consumers of `memory_events` are exposed today (safe cutover surface).

### Authority after cutover

| Concern | Authority |
|---------|-----------|
| Append-only executive/control events | **`portfolio_events` only** |
| Open decision briefs (entities) | `decision_briefs` (unchanged) |
| Strategic beliefs | Hindsight (unchanged; optional nightly synthesis **from** PEL) |
| Ephemeral voice turns | Redis (unchanged; not bulk-migrated into PEL) |
| Failure traces | Guardian JSONL + structured `gate` rows in PEL |

---

## 2. Idempotent migration steps

> Implementation ship applies these. This ship documents only.

### Step 0 — Preconditions

- [ ] Staging/prod `DATABASE_URL` reachable
- [ ] Snapshot or logical backup of `memory_events` (if any rows)
- [ ] Confirm extensions: `pgcrypto` or PG13+ `gen_random_uuid()`
- [ ] Record baseline counts:

```sql
SELECT COUNT(*) AS memory_events_count FROM memory_events;
-- portfolio_events may not exist yet
```

### Step 1 — Create `portfolio_events`

Apply stub DDL from [`07-portfolio-event-log.md` §5](../../../docs/architecture/07-portfolio-event-log.md) (or equivalent migration file under `deploy/migrations/` when that convention lands).

Idempotent: `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`.

### Step 2 — Backfill from `memory_events`

```sql
INSERT INTO portfolio_events (
    timestamp, venture_id, source, type, payload,
    guardian_status, execution_ref, trace_id,
    legacy_memory_event_id, created_at
)
SELECT
    COALESCE(me.created_at, NOW()),
    COALESCE(me.payload->>'venture_id', me.payload->>'project', 'unknown'),
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
```

**Idempotency:** re-running Step 2 must not duplicate rows (`ON CONFLICT DO NOTHING` on `legacy_memory_event_id`).

### Step 3 — Verify backfill

```sql
SELECT
  (SELECT COUNT(*) FROM memory_events) AS src,
  (SELECT COUNT(*) FROM portfolio_events
     WHERE legacy_memory_event_id IS NOT NULL) AS migrated;

-- Expect: migrated = src (when every memory row has a legacy id)

SELECT me.id
FROM memory_events me
LEFT JOIN portfolio_events pe ON pe.legacy_memory_event_id = me.id
WHERE pe.id IS NULL;
-- Expect: 0 rows
```

Spot-check: 5 random rows — `type` = old `event_type`, payload equal, timestamps within 1s.

### Step 4 — Dual-write window (short)

1. Change `retain_structured` (or successor `append_portfolio_event`) to write **PEL first**, then optionally legacy `memory_events` if a feature flag `PEL_DUAL_WRITE_LEGACY=true`.
2. New emit points (frame / fleet / voice) write **only** `portfolio_events`.
3. Duration: until staging verification + one deploy soak (default target ≤ 1 release).

### Step 5 — Cutover writers

1. Set dual-write off; `retain_structured` inserts only into `portfolio_events` (map `event_type` → `type`, fill venture/source defaults).
2. Grep CI guard: fail if new `INSERT INTO memory_events` appears outside migrations.
3. Update MEMORY-STACK / architecture docs to name PEL only.

### Step 6 — Deprecate and drop

After soak + verification that no process reads `memory_events`:

```sql
-- Final migration (separate revision)
DROP TABLE IF EXISTS memory_events;
```

Keep `legacy_memory_event_id` column indefinitely (cheap audit) or drop in a later cleanup.

### Rollback

| Stage | Rollback |
|-------|----------|
| After Step 1–3 only | Drop `portfolio_events`; `memory_events` untouched |
| Dual-write | Disable PEL writers; continue `memory_events` |
| Post-drop | Restore table from backup; not automatic |

---

## 3. Writer inventory (cutover checklist)

| Path today | Target after PEL |
|------------|------------------|
| `postgres_store.retain_structured` → `memory_events` | → `portfolio_events` (`source` default `memory` or caller-provided) |
| Frame runner (no event row) | Emit `type=frame_run` |
| Fleet trigger (no event row) | Emit `type=fleet_trigger` (+ gate rows) |
| Voice intent (Redis turns only) | Emit `type=voice_intent` (not every turn) |
| Aether / squads `MemoryRouter.retain` Postgres types | Same retain path → PEL |

---

## 4. Cross-link: `advoi-analytics-pel-schema-01` acceptance criteria

Implementation ship **`advoi-analytics-pel-schema-01`** owns schema apply + first writers. Design ship acceptance ends at committed docs; implementation acceptance:

### Schema & migration

- [ ] Migration creates `portfolio_events` with columns:  
  `id`, `timestamp`, `venture_id`, `source`, `type`, `payload`, `guardian_status`, `execution_ref`, `trace_id`  
  (+ `legacy_memory_event_id` / `created_at` as designed)
- [ ] Indexes for venture timeline and source/type filters present
- [ ] Backfill from `memory_events` is **idempotent** (second run ⇒ 0 new rows)
- [ ] Verification queries in §2 Step 3 pass on staging
- [ ] `memory_events` either dual-written under flag or fully cut over per plan; no silent dual-authority without flag

### Emit points (minimum for analytics)

- [ ] **Frame run** — `run_frame` completion appends PEL row (`type=frame_run`)
- [ ] **Fleet trigger** — successful/failed `invoke_fleet_trigger` appends PEL row (`type=fleet_trigger`); confirmation path sets `guardian_status`
- [ ] **Voice intent** — resolved intent (not every Redis turn) appends PEL row (`type=voice_intent`)

### Contracts & moat R1

- [ ] T0: every fleet bridge invoke creates ≥1 `portfolio_events` row (moat R1 validation)
- [ ] ADR-026 preserved: no fleet backlog body written as strategic belief; PEL payload excerpts only
- [ ] Optional: T0 unit/contract tests for append helper + mapping from `MemoryEventType`

### Docs & observability

- [ ] `docs/MEMORY-STACK.md` lists `portfolio_events` (and deprecation note for `memory_events` if still present)
- [ ] `docs/architecture/04-memory-and-data.md` links to `07-portfolio-event-log.md`
- [ ] `trace_id` populated when `OTEL_ENABLED=true` (best-effort; NULL allowed when off)

### Explicit non-goals for analytics-schema-01 (unless expanded)

- Full `/api/events` query API (can be stub or follow-up)
- Nightly Hindsight export job
- Dropping `memory_events` on day one (allowed in same ship only if dual-write soak is N/A because empty table)

---

## 5. Risk register

| Risk | Mitigation |
|------|------------|
| Staging has unknown `memory_events` volume | Count first; batch backfill if huge (unlikely) |
| Payload missing venture_id | Default `unknown`; later enrich from execution-context registry |
| Dual-write divergence | Prefer PEL-first; legacy best-effort; short window |
| Analytics assumes CHECK constraints too early | Defer strict CHECKs until writers stable |
| Confusion with `decision_briefs` | Document: briefs = entities; PEL = event log |

---

## 6. Definition of done (this design ship)

- [x] Branch `fm/advoi-data-memory-events-pel-01`
- [x] `docs/architecture/07-portfolio-event-log.md` with PortfolioEvent schema, mapping, emit points, stub SQL
- [x] This migration plan with one-table authority decision + idempotent steps
- [x] Cross-link analytics acceptance criteria
- [x] Docs-only; no runtime behavior change

**Next ship:** `advoi-analytics-pel-schema-01` implements §2–§4.
