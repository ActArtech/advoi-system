# Gaps and blockers

**Last updated:** 2026-07-10  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 validation | Staging redeploy, human E2E | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency | **No** |
| P2 platform | Letta/OTel VPS enable, live squad webhooks | **No** |
| P3 polish | React Flow dashboard, Playwright smoke | **No** |

**Bottom line:** 6-agent control plane is code-complete. Gap is deploy + human validation.

---

## P0 — Validation and deploy parity

### 1. Staging deploy drift (BUG-005)

**Status:** Open until VPS redeploy.

Live staging may show 3 frames, no operators, Aether 404.

**Action:** `cd /opt/advoi && git pull && bash scripts/staging-redeploy.sh`

### 2. Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof:** 190 pytest, agents-smoke (6 agents + run-six + squads + platform).

### 3. Operator fixes need deploy (BUG-006, BUG-007)

Fixed in code @ `fe0d982` / `402f8d3`. Awaiting staging redeploy.

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
| Aether portfolio | Done | Redeploy |
| Guardian auto-restart | Done | Redeploy |
| Squad dispatch | Done (mock) | `ADVOI_SQUAD_MOCK=false` + webhook |
| Operational memory retain | Done | `LETTA_ENABLED=true` optional |
| OTel traces | Done (optional) | `OTEL_ENABLED=true` |
| Dashboard MVP | Done (`/dashboard`) | Redeploy web image |

---

## P3 — Ops and quality

| Gap | Mitigation |
|-----|------------|
| Shelve corrupts `.env` | `ADVOI_SHELVE_PULL=false` |
| Windows pytest hang | Kill stray processes |
| Architecture docs (03/05) still say 3 agents | Update in M0 |

---

## Definition of "ready for production voice"

1. [x] Code: 6 agents, 3 voice paths, operators, squads, dashboard
2. [x] Automated: 190 pytest + smoke scripts
3. [ ] Staging: redeployed 6-agent build
4. [ ] Human Path A sign-off recorded
5. [ ] Letta/OTel enabled on VPS (product depth)

---

## Next priorities

1. **M1** Staging redeploy
2. **M2** Human E2E (15 min)
3. **M4** Letta + OTel on VPS
4. **M5** Live squad webhooks

See [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md).