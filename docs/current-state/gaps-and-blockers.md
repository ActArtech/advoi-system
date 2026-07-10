# Gaps and blockers

**Last updated:** 2026-07-10 (wave 4 wrap-up)  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Wave4 evidence:** [batch-2026-07-10-wave4/summary.md](../../data/feedback-evidence/batch-2026-07-10-wave4/summary.md)  
**Write-path audit:** [advoi-arch-write-path-audit-01/audit.md](../../data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 ops | Staging promote (SSH host key); develop `61de279` vs staging `5d50805` | **No** (blocks T2 only) |
| P0 validation | Human E2E sign-off (incl. A11–A17 chips / home surfaces) | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency human baseline | **No** |
| P1 arch | Write-path V4 voice→fleet import thinning | **No** |
| P2 platform | Letta/OTel VPS apply, live squad webhooks, M10.4 PEL T2, M7 Phase 2, aether cron on VPS | **No** |
| P2 arch | Aether fleet-tree publish vs vertical wording (audit V5) | **No** |
| P3 polish | React Flow, full Playwright connect smoke | **No** |

**Bottom line:** Wave 4 **Aether Queued slice** + **Guardian write-path audit (P0)** are complete on develop. Primary gap remains **SSH-blocked staging promote** + human validation.

---

## P0 — Validation and deploy parity

### 1. Staging promote parked (SSH host key) — GAP-013

**Status:** Parked (wave 2 → wave 3 → wave 4).

Staging remains @ `5d50805`; develop tip `61de279`. SSH host key verification failed on promote/redeploy. Blocks OTEL apply, M10.4 PEL rows, beacon/funnel/gate_export T2, aether feed cron live, and valid A14–A17 human checks on staging tip.

**Action:** Fix host key / `known_hosts`; run promote + `scripts/t2-staging-smoke.sh`.

### 2. Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof:** 494 pytest collected; wave4 suites 105 passed (feed cron / publish atomic / gate export / write-path / fleet); wave3 61; wave2 83 prior.

### 3. Operator fixes (BUG-006, BUG-007) — closed in staging bootstrap

Fixed earlier and verified on staging @ `5d50805`. Re-verify after next promote.

---

## P1 — Functional gaps

| Gap | Status | Notes |
|-----|--------|-------|
| LiveKit two-turn confirm | Open | Confirm parity T0 Done (A15); device test open |
| Path B Kokoro/WebGPU | Mitigated | Path C fallback |
| Full mic-STT-TTS latency | Partial | `run_six_ms` in API diagnostics |
| Local agent cache warmth | Environmental | Use `-WithRedis` on stack script |
| Write-path V4 (voice imports fleet) | Deferred | Still Guardian-gated via `fleet_trigger_from_voice` (ADR-028) |

---

## P2 — Platform enablement

| Gap | Code | VPS |
|-----|------|-----|
| Aether portfolio | Done | Live bootstrap; gate chip T0; proactive schema + feed/publish/export need promote |
| Aether Queued (feed skip / atomic / export) | Done T0 | Cron wire after promote |
| Guardian auto-restart + `trace_id` | Done | Live; OTEL/`trace_id` T2 parked |
| Guardian write-path hard-gate | Done T0 ADR-028 | T2 fleet confirm after promote |
| Squad dispatch | Done (mock) | `ADVOI_SQUAD_MOCK=false` + webhook |
| Operational memory retain | Done | `LETTA_ENABLED=true` optional |
| OTel traces | Done (`697b897`) | `OTEL_ENABLED=true` — **parked SSH** |
| PEL + PWA beacon + funnel + gate_snapshot | Done T0 | M10.4 row proof after promote |
| Dashboard MVP | Done (`/dashboard`) | Live bootstrap |
| PWA interaction shell | Done T0 | Human A11–A17 open |
| Vertical boundaries docs | Done | `06-vertical-boundaries.md` |
| Ingestion Phase 2 (M7) | Partial lifecycle | **Unchanged wave 4** — classifier/UI/batch open |
| Aether fleet-tree publish (audit V5) | Intentional | Revisit vs vertical wording |

---

## P3 — Ops and quality

| Gap | Mitigation |
|-----|------------|
| Shelve corrupts `.env` | `ADVOI_SHELVE_PULL=false` |
| Windows pytest hang | Kill stray processes |
| Architecture docs (03/05) still say 3 agents | Update in M0 / M9.4 |
