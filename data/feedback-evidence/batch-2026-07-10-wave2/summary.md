# Batch wrap-up — wave 2 PWA / analytics / aether (2026-07-10)

**Batch:** AFK continuous loop — PWA shell, PEL beacon, OTEL, fleet idempotency, T2 smoke, aether proactive schema  
**Captain:** First Mate (crewmate wrap-up `advoi-batch-wrapup-wave2-01`)  
**Status:** **Partial** — code complete on develop; staging VPS promote + OTEL apply **parked** (SSH host key)  
**Develop tip:** `ce6a8e2`  
**Prior wrap-up:** `b2ced10` (wave 1 PEL @ `7682b96`)  
**Staging SHA:** `5d50805` (unchanged — promote blocked)

## Done items this wave (8)

| Theme | SHA | Notes |
|-------|-----|-------|
| PWA UI state machine | `3de87ac` | `voiceSessionState.ts` + T0 + e2e stub |
| SLA latency chip | `82b1375` | chip beside state after frame runs |
| OTEL + guardian `trace_id` | `697b897` | moat R6; staging apply parked |
| PWA thin beacon → PEL | `3b7df6c` | `POST /api/events` |
| PWA error recovery | `2c63897` | mic / LiveKit / API 502 |
| fm-bridge 60s idempotency | `70ce1a3` | fleet invoke key |
| Staging T2 CI smoke | `8584da3` | `t2-staging-smoke.sh` + fixtures |
| Aether proactive schema | `ce6a8e2` | JSON Schema + gate validator T0 |

## Smoke / T0

| Check | Result |
|-------|--------|
| Full pytest collection | **366** tests |
| Wave2 suite subset | **83 passed** (see `pytest-wave2.txt`) |
| Suites | `test_voice_session_state`, `test_latency_chip`, `test_otel_setup`, `test_guardian_trace_id`, `test_pwa_beacon_events`, `test_error_recovery`, `test_fleet_idempotency`, `test_t2_staging_smoke`, `test_aether_proactive_schema` |
| Staging live T2 | **Not re-run** — SSH host key verification failed on promote |
| Bootstrap T2 (prior) | Pass 2026-07-10 @ staging `5d50805` |

## Blockers parked

1. **Staging VPS promote + OTEL apply** — SSH host key verification failed  
   - Staging remains @ `5d50805`  
   - Develop @ `ce6a8e2`  
   - Blocks: M1 re-parity, M4.5–M4.6 T2, M10.4 PEL rows, beacon T2, aether proactive live feed  
2. **M2 human E2E** — still open (device); now includes A11–A13  
3. **M5 live webhooks / M4.4 Letta** — deferred (OPP), not wave2 scope

## Decisions

- **No new ADR.** Beacon extends ADR-027; OTEL/idempotency/state machine are implementation.

## Logs updated

- `docs/dev-log/DEV-LOG.md` — wave 2 entry (Status: Partial)  
- `docs/decision-log/DECISION-LOG.md` — no ADR; batch note  
- `docs/current-state/OPPORTUNITIES-LOG.md` — OPP-001 partial; OPP-006–008  
- `docs/current-state/ALIGNMENT-LOG.md` — wave 2 alignment  
- `docs/operations/ROADMAP-VALIDATION.md` — M3/M4/M7/M8/M10 + GAP-013/014  
- `docs/current-state/gaps-and-blockers.md` — SSH promote park  

## Next Queued slice (after wrap-up merge)

1. Fix SSH known_hosts / host key for deploy host  
2. Promote develop → staging; `t2-staging-smoke.sh` + full precheck  
3. Enable OTEL; prove M10.4 + beacon rows  
4. Human E2E M2 when device available  
5. Resume Queued fleet dispatch  

## Resume condition

Mandatory BATCH-DOCUMENTATION artifacts present on branch `fm/advoi-batch-wrapup-wave2-01`. Firstmate merges to `develop` (no PR). Queued dispatch may resume after merge.
