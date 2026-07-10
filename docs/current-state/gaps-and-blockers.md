# Gaps and blockers

**Last updated:** 2026-07-10  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Portfolio strategy:** [PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 validation | Human E2E sign-off | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency | **No** |
| P2 platform | Letta/OTel VPS enable, live squad webhooks, ingestion Phase 2 | **No** |
| P3 polish | React Flow dashboard, Playwright smoke, portfolio event log | **No** |

**Bottom line:** 6-agent control plane is deployed on staging. Primary gap is human validation and platform depth (Letta, OTel, live squads).

---

## P0 — Validation

### 1. Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof:** 224 pytest, agents-smoke (6 agents + run-six + squads + platform), staging precheck pass.

### 2. Staging deploy parity (BUG-005) — closed

**Status:** Done @ `71fd7ae` / `232e172`. Staging shows 6 frames, operator bar, fleet voice intents.

Re-run after code deploy: `bash scripts/staging-redeploy.sh` then T2 precheck.

### 3. Operator fixes (BUG-006, BUG-007) — closed in staging

Fixed in code and deployed. Verify on device during M2 human E2E.

---

## P1 — Functional gaps

| Gap | Status | Notes |
|-----|--------|-------|
| LiveKit two-turn confirm | Open | Device test |
| Path B Kokoro/WebGPU | Mitigated | Path C fallback |
| Full mic-STT-TTS latency | Partial | `run_six_ms` in API diagnostics |
| Local agent cache warmth | Environmental | Use `-WithRedis` on stack script |
| Fleet Guardian confirm on device | Open | API verified; human T3 open |

---

## P2 — Platform enablement

| Gap | Code | VPS |
|-----|------|-----|
| Aether portfolio | Done | Live on staging |
| Guardian confirmation + fleet gate | Done | Live on staging |
| Squad dispatch | Done (mock) | `ADVOI_SQUAD_MOCK=false` + webhook |
| Operational memory retain | Done | `LETTA_ENABLED=true` optional |
| OTel traces | Done (optional) | `OTEL_ENABLED=true` |
| Dashboard MVP | Done (`/dashboard`) | Deployed |
| Ingestion Phase 2 (triage pipeline) | Planned | See `advoi/ingestion/README.md` |
| Portfolio Event Log (PEL) | Planned | See PORTFOLIO-SYSTEM-MOAT R1 |
| Execution Context Registry (ECR) | Planned | See PORTFOLIO-SYSTEM-MOAT R2 |

---

## P3 — Ops and quality

| Gap | Mitigation |
|-----|------------|
| Shelve corrupts `.env` | `ADVOI_SHELVE_PULL=false` |
| Windows pytest hang | Kill stray processes |
| Architecture docs (03/05) still say 3 agents | Update in M0 / generated manifest |
| Aether active venture vs fleet project mismatch | ECR (gem-dev-shop vs clapart) |
| Fleet runtime data not in git | PEL + fleet event export |

---

## Definition of "ready for production voice"

1. [x] Code: 6 agents, 3 voice paths, operators, squads, dashboard, ingestion MVP, fm-bridge
2. [x] Automated: 224 pytest + smoke scripts
3. [x] Staging: redeployed 6-agent build
4. [ ] Human Path A sign-off recorded
5. [ ] Letta/OTel enabled on VPS (product depth)
6. [ ] Portfolio event log for consequential actions (moat v1)

---

## Next priorities

1. **M2** Human E2E (15 min)
2. **M4** Letta + OTel on VPS
3. **M5** Live squad webhooks
4. **M7** Ingestion Phase 2 + PEL/ECR (holistic)

See [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md) and [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md).