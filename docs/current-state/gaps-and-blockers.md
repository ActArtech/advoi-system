# Gaps and blockers

**Last updated:** 2026-07-10 (wave 2 wrap-up)  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Wave2 evidence:** [batch-2026-07-10-wave2/summary.md](../../data/feedback-evidence/batch-2026-07-10-wave2/summary.md)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 ops | Staging promote (SSH host key); develop `ce6a8e2` vs staging `5d50805` | **No** (blocks T2 only) |
| P0 validation | Human E2E sign-off (incl. A11–A13) | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency human baseline | **No** |
| P2 platform | Letta/OTel VPS apply, live squad webhooks, M10.4 PEL T2 | **No** |
| P3 polish | React Flow, full Playwright connect smoke | **No** |

**Bottom line:** Wave 2 code (PWA shell, PEL beacon, OTEL wiring, T2 smoke, aether proactive schema) is on develop. Primary gap is **SSH-blocked staging promote** + human validation.

---

## P0 — Validation and deploy parity

### 1. Staging promote parked (SSH host key) — GAP-013

**Status:** Parked (wave 2).

Staging remains @ `5d50805`; develop tip `ce6a8e2`. SSH host key verification failed on promote/redeploy. Blocks OTEL apply, M10.4 PEL rows, beacon T2, aether proactive live.

**Action:** Fix host key / `known_hosts`; run promote + `scripts/t2-staging-smoke.sh`.

### 2. Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof:** 366 pytest collected; wave2 suites 83 passed (state/latency/recovery/beacon/OTEL/idempotency/T2 fixtures/aether schema).

### 3. Operator fixes (BUG-006, BUG-007) — closed in staging bootstrap

Fixed earlier and verified on staging @ `5d50805`. Re-verify after next promote.

---

## P1 — Functional gaps

| Gap | Status | Notes |
|-----|--------|-------|
| LiveKit two-turn confirm | Open | Device test |
| Path B Kokoro/WebGPU | Mitigated | Path C fallback |
| Full mic-STT-TTS latency | Partial | `run_six_ms` in API diagnostics |
| Local agent cache warmth | Environmental | Use `-WithRedis` on stack script |

---

## P2 — Platform enablement

| Gap | Code | VPS |
|-----|------|-----|
| Aether portfolio | Done | Live bootstrap; proactive schema T0 @ `ce6a8e2` needs promote |
| Guardian auto-restart + `trace_id` | Done | Live; OTEL/`trace_id` T2 parked |
| Squad dispatch | Done (mock) | `ADVOI_SQUAD_MOCK=false` + webhook |
| Operational memory retain | Done | `LETTA_ENABLED=true` optional |
| OTel traces | Done (`697b897`) | `OTEL_ENABLED=true` — **parked SSH** |
| PEL + PWA beacon | Done (`7682b96` + `3b7df6c`) | M10.4 row proof after promote |
| Dashboard MVP | Done (`/dashboard`) | Live bootstrap |
| PWA state / latency / recovery | Done T0 | Human A11–A13 open |

---

## P3 — Ops and quality

| Gap | Mitigation |
|-----|------------|
| Shelve corrupts `.env` | `ADVOI_SHELVE_PULL=false` |
| Windows pytest hang | Kill stray processes |
| Architecture docs (03/05) still say 3 agents | Update in M0 |

---

## Definition of "ready for production voice"

1. [x] Code: 6 agents, 3 voice paths, operators, squads, dashboard, PEL, PWA shell hardening
2. [x] Automated: 366 pytest + T2 smoke script
3. [~] Staging: bootstrap @ `5d50805`; wave2 promote **parked** (SSH)
4. [ ] Human Path A sign-off recorded (A11–A13 included)
5. [ ] Letta/OTel enabled on VPS (product depth)
6. [ ] M10.4 PEL staging row proof

---

## Next priorities

1. **GAP-013** Fix SSH host key → promote develop → staging T2
2. **M2** Human E2E (15 min) including A11–A13
3. **M4** Letta + OTel on VPS (code ready for OTel)
4. **M5** Live squad webhooks
5. **M7** Ingestion Phase 2 classifier polish

See [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md) and [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md).