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

## fm-bridge invoke idempotency (60s)

- **Module:** `advoi/fleet/idempotency.py` — process-local in-memory cache, default window **60s** (`ADVOI_FLEET_IDEMPOTENCY_WINDOW_SECS`).
- **Contract:** clients pass opaque key via HTTP header `Idempotency-Key` (wins) **or** JSON `idempotency_key` on `POST /api/fleet/trigger`. Same key within the window returns prior terminal result with `deduped: true` and does **not** re-run `fm-bridge.sh`.
- **Not cached:** `confirmation_required` (so confirmed retry with same key still dispatches).
- **Scope:** single API worker; multi-replica needs a future shared store.
- **T0:** `tests/test_fleet_idempotency.py`.

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

## PWA Aether gate chip (ship #3)

- Chip beside state + SLA: `data-testid="aether-gate-chip"`; also on `/dashboard` metrics row.
- Fed by `GET /api/aether/status` (`gate.verdict`, `gate.active_slug`).
- Pure model: `web/components/aetherGateChip.ts` → `aetherGateChipModel`; Python mirror `tests/test_aether_gate_chip.py`.
- Label: `Gate pass · {active_slug}` (tones: pass=ok, hold=warn, fail=error); missing/err → `Gate —` / `Gate err`.
- Manual matrix A14 in `docs/operations/MANUAL-TEST-TRACKER.md`.

## PWA thin beacon → PEL (`POST /api/events`)

- **Endpoint:** `POST /api/events` accepts thin client beacons only (no third-party analytics SDK).
- **Allowed types:** `pwa_connect`, `frame_tap`, `confirm_shown`, `confirm_accept`, `error` (`PWA_BEACON_EVENT_TYPES` in `advoi/analytics/pel.py`).
- **Persist:** same `append_event` path → `portfolio_events` (`source=api`, payload includes `client: pwa`).
- **PWA wire:** `web/components/pwaBeacon.ts` + `dispatchUi` wrapper in `VoiceSession.tsx` maps UI state-machine events (`CONNECT_OK`→`pwa_connect`, `FRAME_START`→`frame_tap`, `CONFIRMATION_REQUIRED`→`confirm_shown`, `CONNECT_FAIL`/`ERROR`→`error`); confirm taps emit `confirm_accept` explicitly.
- **T0:** `tests/test_pwa_beacon_events.py` (insert + schema per type).

## PWA confirm parity (voice + tap)

When Guardian returns `confirmation_required`, Path A must show **identical** confirm copy on voice TTS and tap UI (moat 7.4).

- Pure model: `web/components/confirmParity.ts` → `confirmCopyFromResponse` / `confirmParityModel` (prefer `prompt` → `spoken_summary` → `spoken`).
- Wire: `VoiceSession` stores `confirmUi`, enters UI state `confirm_pending`, panel `data-testid="confirm-pending"` with `confirm-copy` + **Confirm** button `confirm-accept`.
- Beacons: `CONFIRMATION_REQUIRED` → `confirm_shown` (payload includes `confirm_copy`); accept → `confirm_accept`.
- T0/API: `tests/test_confirm_parity.py`. Manual matrix A15. Stub: `web/e2e/voice-session-confirm-parity.spec.ts`.

## PWA error recovery paths

Path A recovery panel when UI state is `error` (`data-testid="error-recovery"`):

| Kind | Affordance | Path C `/voice-server` |
|------|------------|------------------------|
| `mic_denied` | Clear message + Retry connect | No |
| `livekit_connect` | Retry connect | Yes |
| `api_frame` (incl. 502) | Retry request (re-runs frame when known) | Yes |

- Pure model: `web/components/errorRecovery.ts` (`classifyConnectError`, `classifyApiError`, `errorRecoveryModel`).
- Wire: `VoiceSession` surfaces recovery via `CONNECT_FAIL` / `ERROR` + beacon payload `recovery_kind`.
- T0: `tests/test_error_recovery.py`. Manual matrix A13 in `docs/operations/MANUAL-TEST-TRACKER.md`.

## OTel staging + Guardian trace_id (moat R6)

- **Switch:** `OTEL_ENABLED=true` in `deploy/.env.staging.example`; local default off in `.env.example`.
- **Endpoint:** gRPC OTLP on **4317** (`opentelemetry-exporter-otlp-proto-grpc`). Do not use HTTP 4318 for this exporter.
- **Images:** `Dockerfile.api` / `Dockerfile.voice` install `[observability]` extras.
- **Collector:** compose profile `observability` → `otel-collector`; `scripts/staging-redeploy.sh` starts it when `OTEL_ENABLED=true`.
- **Guardian JSONL:** `append_guardian_event` adds top-level `trace_id` when OTEL is on (`advoi/memory/guardian_log.py` + `current_trace_id` in `otel_setup`).
- **Diagnostics:** `GET /api/diagnostics/platform` → `otel.otel_ready` / top-level `otel_ready` (enabled + packages + TCP collector reachable).
- **T0:** `tests/test_guardian_trace_id.py`, `tests/test_otel_setup.py`. Staging steps in `docs/operations/MANUAL-TEST-TRACKER.md` (O5 / OT1–OT4).
- **VPS:** promote/SSH may be parked — land on `develop` first; apply env on VPS when reachable.

## Staging T2 smoke

- Post-deploy minimum gate: `scripts/t2-staging-smoke.sh` (default base `https://advoi-staging.keyteller.com`).
- Asserts `GET /api/health` with `agents_ready=6` and `agents_total=6`, and `GET /api/aether/status` shape (`gate`, `frame_coverage`, `memory.letta_health`).
- Exits non-zero on failure; called at end of `scripts/staging-redeploy.sh`.
- Offline parse tests: `bash scripts/t2-staging-smoke.sh --fixture-dir tests/fixtures/t2-smoke` and `uv run pytest tests/test_t2_staging_smoke.py`.
- Validators live in `scripts/t2_validate.py` (no network).

## Aether proactive feed schema

- **Artifact:** `docs/aether/aether-proactive-latest.json` (FirstMate `fm-aether-gate.sh` input when `FM_ACTIVE_PROJECT=advoi`).
- **JSON Schema:** `docs/aether/aether-proactive-latest.schema.json` — required `project`, `mode`=`proactive`, non-empty `findings[]` with `agent`/`severity`/`category`/`message`.
- **Validator:** `advoi.aether.proactive_schema.validate_proactive_payload` / `validate_proactive_file` (stdlib-only Draft subset; no `jsonschema` dep).
- **T0:** `tests/test_aether_proactive_schema.py` (fixtures under `tests/fixtures/aether-proactive/`) + `tests/test_aether_gate_artifacts.py`.
