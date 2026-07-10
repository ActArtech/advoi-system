# Architecture, data, memory, and vertical logic review

**Date:** 2026-07-10  
**Baseline:** `advoi-system` @ develop, staging @ https://advoi-staging.keyteller.com  
**Companion:** [PORTFOLIO-SYSTEM-MOAT.md](PORTFOLIO-SYSTEM-MOAT.md) · [04-memory-and-data.md](../architecture/04-memory-and-data.md) · [MEMORY-STACK.md](../MEMORY-STACK.md)

---

## Executive summary

Code has outpaced architecture docs. Runtime ships **6 agents / 6 frames**, built **Aether, Guardian, Squads, Ingestion** verticals, and a working **ADR-026 memory router** — but `01-system-overview.md` and `03-multi-agent.md` still describe Stage 1 stubs (3 agents).

**Strongest layer:** `write_targets.py` + `MemoryRouter` — explicit tiers, no double-write rule.

**Weakest layers:** (1) triple brief read path (Redis + Postgres + Hindsight), (2) no ontology enforcement, (3) `memory_events` vs planned PEL overlap, (4) ingestion lifecycle missing triage/approve states, (5) schema via inline `CREATE TABLE` without migrations.

---

## Vertical architecture (domain modules)

| Vertical | Path | Code status | Doc status | Gap |
|----------|------|-------------|------------|-----|
| Voice | `advoi/voice/` | Built — Pipecat, intents, operators, memory hooks | Partial | Path B/C matrix incomplete |
| Routing | `advoi/routing/` | Built — 6 daemons, frame_runner, supervisor | **Stale** (doc says 3) | Cache TTL policy undocumented |
| Decision | `advoi/decision/` | Built — 6 frames | **Stale** (doc says 3) | No generated manifest |
| Memory | `advoi/memory/` | Built — router, bridge, postgres, redis, letta fallback | Good (ADR-026) | Brief triple-path; review queue partial |
| Aether | `advoi/aether/` | Built — gate, portfolio, architect hooks | Doc says stub | Gate artifacts VPS-only |
| Guardian | `advoi/guardian/` | Built — confirm, recovery, notifications | Doc says stub | Not all write paths audited |
| Squads | `advoi/squads/` | Built — registry, dispatch, mock webhooks | Doc says stub | Live webhook contract open |
| Fleet | `advoi/fleet/` | Built — bridge, trigger, session | Good | No idempotency; no PEL mirror |
| Ingestion | `advoi/ingestion/` | MVP built | Doc says stub | Status enum missing triage/approve |
| API | `advoi/api/` | Built | Good | No `/api/events` yet (PEL) |

### Vertical boundary rules (target)

```text
voice     → routing (frames/intents) → vertical backends (fleet, memory, aether)
          → never: voice → fleet shell directly

guardian  → gates ALL consequential writes (fleet, ingestion dispatch, review queue)

memory    → write_targets only; no module calls Hindsight directly except via MemoryRouter

aether    → read gate + portfolio; enrich frames; no fleet writes

ingestion → route → (approve) → guardian → fleet
```

**Violation to audit:** any `fm-bridge` or `retain_strategic` call outside Guardian + MemoryRouter paths.

---

## Horizontal architecture

| Horizontal | Path | Status | Gap |
|------------|------|--------|-----|
| Ontology | `advoi/ontology/` | **Empty stub** | Frames/agents hardcoded; no venture_id validation |
| Observability | `advoi/observability/` | OTel optional | Off on staging; no trace_id in guardian log |
| Reporting | `advoi/reporting/` | Stub | No BI on memory_events |
| Ingestion | (also vertical) | MVP | Phase 2 state machine |

---

## Data architecture

### Stores and authority

| Store | Canonical for | Consumers | Problem |
|-------|---------------|-----------|---------|
| Postgres `decision_briefs` | Open briefs (claimed) | Brief Curator | Competes with Redis + Hindsight |
| Postgres `memory_events` | Structured retain mirror | None exposed | Overlaps planned `portfolio_events` |
| Postgres `review_queue` | Deep review items | Review frame + `/api/review-queue` | Canonical; CRUD enqueue/list/get/dequeue |
| Redis `advoi:briefs:open` | Fast brief cache | Brief Curator | Can drift from Postgres |
| Redis `advoi:agent:*:last` | Agent last_run cache | PWA, `/api/agents` | TTL = 2x daemon interval only |
| Redis voice turns | Ephemeral session | Voice recall | No documented max window |
| Hindsight | Strategic beliefs | Brief Curator, voice recall | Must not store fleet backlog |
| Filesystem ingestion | Upload blobs + metadata | `/ingest` UI | No Paperclip id link |
| Fleet files | Backlog, crew state | Fleet scout, fm-bridge | Not versioned |

### Ingestion lifecycle (gap)

Current `IngestStatus`: `uploaded | routed | dispatched | failed`

Required (M7 / moat Pattern C): `uploaded → triaged → needs_review → approved → dispatched`

### Schema management (gap)

Tables created inline in `postgres_store.py`, `review_queue.py` — no migration history, no staging/live schema drift detection.

---

## Memory architecture (ADR-026)

### What works

- `EVENT_WRITE_MAP` — one primary target set per `MemoryEventType`
- `MemoryRouter.recall/retain` — single entry point
- memory-bridge isolates docker.sock to one service
- Tests in `test_memory.py` for write target routing

### Gaps

| Gap | Risk | Fix |
|-----|------|-----|
| Brief Curator merges 3 sources | Stale/contradictory spoken briefs | Postgres canonical → Redis cache invalidate |
| `memory_events` ≠ PEL | Two event tables, unclear authority | Merge schema into `portfolio_events` |
| No retain audit | Silent retain failures (`debug` log) | Retain result metrics + Guardian on failure |
| Letta path untested on VPS | Operational memory JSONL only | Staging enable + recall test |
| No compaction | Postgres/Redis growth | TTL job for memory_events + voice turns |
| Fleet data in recall | Moat erosion if Hindsight stores queue | Audit retain payloads for fleet text |

### Memory tier decision table (enforce in code review)

| Question | Answer from | Never from |
|----------|-------------|------------|
| What is fleet doing? | Fleet files + PEL/bridge event | Hindsight |
| What did we decide? | Postgres briefs + Hindsight governance | Redis turns |
| What failed? | Guardian JSONL | Letta |
| What did user prefer? | Letta (when on) | Fleet backlog |

---

## System logic flows to validate

1. **Frame run:** PWA/API → frame_runner → agent backend → Redis cache → spoken_summary
2. **Voice intent:** transcript → capabilities → respond → Guardian? → frame or fleet
3. **Fleet trigger:** API → Guardian evaluate → fm-bridge → fleet tree (side effect)
4. **Ingestion:** upload → parse → route → [missing approve] → dispatch
5. **Post-frame Aether:** frame result → architect.post_frame_aether → retain squad_lesson/belief

Each flow needs: PEL row (when built), Guardian record on writes, trace_id (when OTel on).

---

## Recommended ship order (fleet backlog)

```text
1. arch doc reconciliation (01, 03 multi-agent)
2. memory retain audit + brief single canonical path
3. ingestion status enum + approve gate
4. memory_events → portfolio_events PEL merge
5. ontology registry + frame validator
6. schema migrations + staging drift check
7. review_queue Postgres completion
8. Letta staging path verification
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Initial review: vertical/horizontal map, data authority table, ADR-026 gaps, ingestion lifecycle, fleet backlog |