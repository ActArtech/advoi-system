# Development milestones (prioritized)

**Updated:** 2026-07-10  
**Baseline:** Build 1.5+ with 6-agent control plane @ `25af012`

---

## Status legend

| Symbol | Meaning |
|--------|---------|
| Done | Shipped in code + tests |
| Partial | Core shipped; VPS/human validation open |
| Open | Not started or stub only |

---

## M0 — Doc reconciliation

| Task | Status |
|------|--------|
| SYSTEM-STATUS aligned to 6 agents | **Done** (2026-07-10) |
| WHAT-WE-DID sprint doc | **Done** |
| Architecture 03/05 updated to 6 daemons | Open |
| Stale PLAN-SETUP-REVIEW banner | Partial |

---

## M1 — Staging deploy parity (P0)

| Task | Status | Verify |
|------|--------|--------|
| `git pull` + `staging-redeploy.sh` on VPS | **Open** | 6 frames on PWA |
| Post-deploy smoke | **Open** | agents-smoke + voice-smoke pass |
| Aether APIs live | **Open** | `/api/aether/status` 200 |
| Operator bar on staging | **Open** | Run all 6, stop/restart visible |

**Closes:** BUG-005, BUG-006, BUG-007

---

## M2 — Human voice sign-off (P0)

| Task | Status |
|------|--------|
| Path C `/voice-server` spot check | Open |
| Path A staging mic → TTS | Open |
| Two-turn confirm on device | Open |
| Home briefs + review queue (A17) | Open (T0 done) |
| Chips / recovery / confirm parity (A11–A15) | Open (T0 done) |
| Install + morning pulse (A16) | Open (T0 done) |
| E2E-SIGNOFF.md PASS recorded | Open |

---

## M3 — Voice hardening (P1)

| Task | Status |
|------|--------|
| `run_six_ms` in latency diagnostics | **Done** |
| Voice run-all + dispatch_squads tests | **Done** |
| Path B WebGPU matrix documented | Open |
| Full mic round-trip latency baseline | Open |
| Playwright PWA connect smoke | Open |

---

## M4 — Memory + OTel (P2)

| Task | Status |
|------|--------|
| Operational memory retain on run-six | **Done** |
| `GET /api/diagnostics/platform` | **Done** |
| Letta code + JSONL fallback | **Done** |
| `LETTA_ENABLED=true` on VPS | Open |
| `OTEL_ENABLED=true` + collector | Open |

---

## M5 — Squad bridge (P2)

| Task | Status |
|------|--------|
| Squad registry (4 squads) | **Done** |
| dispatch-all + run-six integration | **Done** |
| Voice "dispatch all squads" | **Done** |
| Live Discord/FirstMate webhook | Open |
| `ADVOI_SQUAD_MOCK=false` on staging | Open |

---

## M6 — Dashboard (P3)

| Task | Status |
|------|--------|
| `/dashboard` squad/agent graph MVP | **Done** |
| Run 6 + dispatch from dashboard | **Done** |
| React Flow interactive graph | Open |
| Ingestion stub | Open |

---

## M7 — Security + production (P3)

| Task | Status |
|------|--------|
| API auth for staging PWA | Open |
| docker.sock blast radius doc | Open |
| Deploy rollback runbook | Partial (staging-runbook exists) |

---

## Recommended sequence

```
M1 staging deploy → M2 human E2E → M4 Letta/OTel on VPS → M5 live squads → M6 React Flow
```

Development is **not blocked** on M2. Continue M4-M6 enablement in parallel with human testing.

---

## Success metrics (today)

| Metric | Target | Actual |
|--------|--------|--------|
| pytest | 100% pass | **190/190** |
| agents-smoke | 6 agents + run-six | Pass locally |
| advoi-orchestrate six-squads | 6 frames + 4 squads | Pass (~6s) |
| Staging parity | 6 frames live | **Open** (redeploy) |
| Human E2E | Recorded PASS | **Open** |