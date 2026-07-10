# Gaps and blockers

**Last updated:** 2026-07-10 (ops review vs live staging @ develop `3d5a00d`)  
**Authoritative snapshot:** [SYSTEM-STATUS.md](SYSTEM-STATUS.md)  
**Sprint log:** [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
**Validation roadmap:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md)  
**Ops runbooks:** [staging-runbook.md](../operations/staging-runbook.md) · [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md)  
**Alignment (drift):** [ALIGNMENT-LOG.md](ALIGNMENT-LOG.md) — ops-review + staging-record  
**Wave4 evidence:** [batch-2026-07-10-wave4/summary.md](../../data/feedback-evidence/batch-2026-07-10-wave4/summary.md) · [blockers.md](../../data/feedback-evidence/batch-2026-07-10-wave4/blockers.md)  
**Write-path audit:** [advoi-arch-write-path-audit-01/audit.md](../../data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md)  
**Fleet state:** `/data/staging-state.md` (develop tip / VPS SHA / promote blocker)

---

## Summary

| Priority | Open items | Blocks coding? |
|----------|------------|----------------|
| P0 ops | Staging promote (SSH host key GAP-013); develop `3d5a00d` vs staging `5d50805` | **No** (blocks tip T2 only; bootstrap T2 **pass**) |
| P0 validation | Human E2E sign-off (incl. A11–A17 chips / home surfaces) | **No** |
| P1 functional | Device confirm, Path B/iOS, mic latency human baseline | **No** |
| P1 arch | Write-path V4 voice→fleet import thinning | **No** |
| P2 platform | Letta/OTel VPS apply, live squad webhooks, M10.4 PEL T2, M7 Phase 2, aether cron on VPS | **No** |
| P2 arch | Aether fleet-tree publish vs vertical wording (audit V5) | **No** |
| P3 polish | React Flow, full Playwright connect smoke | **No** |

**Bottom line:** Develop tip `3d5a00d` (paperclip ingest link; prior data migrations @ `19b052d`, wave-4 Aether/arch @ `61de279`) is **ahead** of staging VPS `5d50805`. Primary gap remains **SSH-blocked staging promote** + human validation. Bootstrap staging still smokes green — that is **not** tip parity.

---

## P0 — Validation and deploy parity

### 1. Staging promote parked (SSH host key) — GAP-013

**Status:** Parked (wave 2 → wave 3 → wave 4 → staging-record → ops-review).

Staging VPS tree remains @ `5d50805`; develop tip `3d5a00d`. SSH host key verification failed on promote/redeploy. Blocks OTEL apply, M10.4 PEL rows, beacon/funnel/gate_export T2, aether feed cron live, migrations/briefs/paperclip fields on VPS, and valid A14–A17 human checks on staging tip.

**T2 note (re-verified 2026-07-10):** Bootstrap SHA **passes** at https://advoi-staging.keyteller.com:
- `GET /api/health` → 200, `agents_ready=6` / `agents_total=6`, `stage=voice-pwa-2`
- `bash scripts/t2-staging-smoke.sh` → exit 0 (health + aether/status)
- `ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh` → exit 0
- Latency SLA still open: `sla_ok=false` (~1.2s API voice path vs 800ms target)

**What T2 pass proves:** runtime on **bootstrap** SHA `5d50805` is healthy.  
**What it does not prove:** wave 2–4 code, data migrations, paperclip ingest, or any develop tip after `5d50805` on VPS.

**Action:** Fix host key / `known_hosts`; run promote + `scripts/t2-staging-smoke.sh` + precheck with `ADVOI_BASE_URL=https://advoi-staging.keyteller.com`.  
**Evidence:** `data/feedback-evidence/batch-2026-07-10-wave4/blockers.md` · fleet `/data/staging-state.md`

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
