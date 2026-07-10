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

- **Authority:** append-only Postgres `portfolio_events` is the control-plane event log. Do **not** drop `memory_events` until soak (migration-plan deprecation checklist).
- **Write API:** `advoi.analytics.pel.append_event` / `safe_append_event`; enums `EventSource`, `EventType`, `GuardianStatus`.
- **Migration:** `deploy/migrations/001_portfolio_events.sql` (create + idempotent backfill). Inline `CREATE IF NOT EXISTS` also runs on first append when `DATABASE_URL` is set.
- **Tests:** set `ADVOI_PEL_MEMORY=true` for in-memory rows (`memory_rows()` / `reset_memory_store()`); T0 `tests/test_portfolio_events.py`.
- **Emit points:** `run_frame` → `frame_run`; `invoke_fleet_trigger` → `fleet_trigger`; confirmation → `guardian_gate`; voice frame/operator only → `voice_intent` (not Redis turns).
- **ADR-026:** PEL is not a live Hindsight double-write. Payload excerpts only — no full fleet backlog dumps.
- **Staging T2:** ROADMAP M10.4 — verify rows after fleet/frame on VPS Postgres.

## PWA voice UI state machine

Path A (`web/components/VoiceSession.tsx`) uses an explicit UI state machine in
`web/components/voiceSessionState.ts`:

`idle` → `connecting` → `connected` → `frame_running` → `confirm_pending` → `error`

- Transitions: LiveKit connect, frame/fleet/intent APIs, Guardian `confirmation_required`.
- Visible status chip: `data-testid="ui-state-chip"` / `data-state={state}`.
- Pure reducer unit-tested via `tests/test_voice_session_state.py` (keep TS + Python in sync).
- Playwright stub: `web/e2e/voice-session-state.spec.ts` (not CI-wired).

## PWA SLA latency chip (ship #2)

- Chip sits beside the state chip: `data-testid="sla-latency-chip"`.
- Fed by `GET /api/diagnostics/latency` (`timings_ms.frame_run_ms`, `timings_ms.run_six_ms`, `sla_ok`).
- Pure model: `web/components/latencyChip.ts` → `latencyChipModel`; Python mirror `tests/test_latency_chip.py`.
- VoiceSession refreshes latency after successful frame run / operator completion (no full reload).
- Graceful empty/error: `SLA —` / `SLA err` when diagnostics unavailable.
