# Gaps and blockers

**Last updated:** 2026-07-10 (post-promote @ develop `ecccc97` / staging aligned)  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Ops runbooks:** [staging-runbook.md](../operations/staging-runbook.md) · [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md)  
**Incident playbook:** [ADVOI-VPS-INCIDENT-PLAYBOOK.md](../operations/ADVOI-VPS-INCIDENT-PLAYBOOK.md)  
**Fleet state:** `data/staging-state.md` (develop = staging @ `414971a`+)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 validation | Human E2E sign-off (A11–A17, voice confirm on device) | **No** |
| P1 platform | OTEL_ENABLED + LETTA_ENABLED on staging VPS env | **No** |
| P1 analytics | PEL gate_snapshot emit on every gate PASS (wired; verify cron) | **No** |
| P1 ops | Live cutover (`/opt/advoi` legacy) | **No** (captain approval) |
| P2 functional | Device confirm, Path B/iOS, full mic-STT-TTS latency | **No** |
| P2 platform | Live squad webhooks, ECR registry | **No** |
| P3 polish | React Flow depth, full Playwright connect smoke | **No** |

**Bottom line:** Staging VPS is **aligned** with develop (`414971a` stack + ops commits). T2 precheck **pass** @ https://advoi-staging.keyteller.com. GAP-013 SSH promote blocker **cleared** (host promote only). Primary remaining gaps: **human T3 E2E**, **VPS env flags (OTEL/LETTA)**, and **live cutover**.

---

## Closed (2026-07-10)

| Gap | Resolution |
|-----|------------|
| GAP-013 SSH promote | Host `promote-to-staging.sh`; never container SSH |
| Staging behind develop (`5d50805`) | Promoted to `414971a`; T2 pass |
| `docker-compose.www.yml` untracked | Committed @ `ecccc97` |
| Stale backlog / gaps doc | Synced this file + fleet backlog |
| GitHub CI as ship gate | Disabled push triggers; VPS T0/T2 only |
| PEL gate_snapshot = 0 | `aether-gate-export.sh` + post-gate hook in `fm-aether-gate.sh` |

---

## P0 — Human validation

### Human E2E voice not signed off

**Status:** Open — [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md)

**Automated proof @ staging tip:**
- `staging-signoff-precheck.sh` exit 0
- 625+ pytest on develop; T2 curls green
- `/api/diagnostics/latency` `sla_ok=true` (API path; not full mic round-trip)

---

## P1 — Platform (VPS env, not code)

| Gap | Code | VPS action |
|-----|------|------------|
| OTEL trace_id in guardian JSONL | Done @ `697b897` | Set `OTEL_ENABLED=true` on staging `.env`, redeploy |
| LETTA executive agent | Scaffolded | Set `LETTA_ENABLED=true` when Letta service ready |
| Live squad webhooks | Partial | Captain: live env + smoke |
| PEL gate_snapshot | `gate_export.py` + export script | Auto after gate PASS; verify `payload.kind=gate_snapshot` in Postgres |

---

## P1 — Functional

| Gap | Status | Notes |
|-----|--------|-------|
| LiveKit two-turn confirm | Open (T3) | T0 confirm parity done (A15) |
| Path B Kokoro/WebGPU | Mitigated | Path C fallback |
| Full mic-STT-TTS latency | Partial | `run_six_ms` in diagnostics only |
| Write-path V4 (voice imports fleet) | Deferred | Guardian-gated ADR-028 |

---

## P2 — Moat / architecture

| Gap | Status |
|-----|--------|
| Execution Context Registry (ECR) | Queued `adv-moat-ecr-r2` |
| Aether fleet-tree publish wording | Audit V5 deferred |

---

## Deploy parity (current)

| Tier | SHA | Note |
|------|-----|------|
| Develop | `ecccc97` | compose.www + playbook + gate export hook |
| Staging VPS | `414971a` | promote pending after tip commits |
| T2 smoke | **PASS** | 6/6 agents, precheck exit 0 |

**After next promote:** re-run T2; confirm `governance_decision` PEL rows with `kind=gate_snapshot` in staging Postgres.