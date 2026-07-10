# Gaps and blockers

**Last updated:** 2026-07-10 (wave 3 wrap-up)  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Wave3 evidence:** [batch-2026-07-10-wave3/summary.md](../../data/feedback-evidence/batch-2026-07-10-wave3/summary.md)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 ops | Staging promote (SSH host key); develop `587385d` vs staging `5d50805` | **No** (blocks T2 only) |
| P0 validation | Human E2E sign-off (incl. A11–A17 chips / home surfaces) | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency human baseline | **No** |
| P2 platform | Letta/OTel VPS apply, live squad webhooks, M10.4 PEL T2, M7 Phase 2 | **No** |
| P3 polish | React Flow, full Playwright connect smoke | **No** |

**Bottom line:** Wave 3 **PWA interaction Queued slice** is complete on develop (gate chip, confirm parity, onboarding, home briefs, funnel doc). Primary gap remains **SSH-blocked staging promote** + human validation.

---

## P0 — Validation and deploy parity

### 1. Staging promote parked (SSH host key) — GAP-013

**Status:** Parked (wave 2 → wave 3).

Staging remains @ `5d50805`; develop tip `587385d`. SSH host key verification failed on promote/redeploy. Blocks OTEL apply, M10.4 PEL rows, beacon/funnel T2, aether proactive live, and valid A14–A17 human checks on staging tip.

**Action:** Fix host key / `known_hosts`; run promote + `scripts/t2-staging-smoke.sh`.

### 2. Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof:** 415 pytest collected; wave3 suites 61 passed (gate chip / confirm parity / onboarding / home briefs / beacon); wave2 suites 83 prior (state/latency/recovery/OTEL/idempotency/T2 fixtures/aether schema).

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

---

## P2 — Platform enablement

| Gap | Code | VPS |
|-----|------|-----|
| Aether portfolio | Done | Live bootstrap; gate chip T0 @ `6c01c1c`; proactive schema needs promote |
| Guardian auto-restart + `trace_id` | Done | Live; OTEL/`trace_id` T2 parked |
| Squad dispatch | Done (mock) | `ADVOI_SQUAD_MOCK=false` + webhook |
| Operational memory retain | Done | `LETTA_ENABLED=true` optional |
| OTel traces | Done (`697b897`) | `OTEL_ENABLED=true` — **parked SSH** |
| PEL + PWA beacon + funnel doc | Done | M10.4 row proof after promote |
| Dashboard MVP | Done (`/dashboard`) | Live bootstrap |
| PWA interaction shell | Done T0 | Human A11–A17 open |
| Ingestion Phase 2 (M7) | Partial lifecycle | **Unchanged wave 3** — classifier/UI/batch open |

---

## P3 — Ops and quality

| Gap | Mitigation |
|-----|------------|
| Shelve corrupts `.env` | `ADVOI_SHELVE_PULL=false` |
| Windows pytest hang | Kill stray processes |
| Architecture docs (03/05) still say 3 agents | Update in M0 |
