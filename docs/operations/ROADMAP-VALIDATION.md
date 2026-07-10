# ADVoi roadmap with validation tiers

**Purpose:** Single checklist for what to build next and how to prove each milestone before moving on.  
**Baseline:** 2026-07-10, repo `advoi-system` develop tip `2b9a28e` (ADR-027/028 stubs; paperclip ingest `3d5a00d`; prior wave-4 `61de279` + data `19b052d`) · staging VPS still `5d50805`  
**Last T2 validation:** 2026-07-10 — `t2-staging-smoke.sh` + `staging-signoff-precheck.sh` exit 0 @ **bootstrap** SHA; **re-promote parked** (GAP-013 SSH host key) — evidence `data/feedback-evidence/batch-2026-07-10-wave4/` · fleet `/data/staging-state.md`  
**T2 pass scope:** Proves healthy runtime on VPS tree `5d50805` only — **not** develop tip parity (waves 2–4, migrations, paperclip, decision stubs).  
**Staging (fleet tier):** https://advoi-staging.keyteller.com (`/var/www/advoi/staging`, compose `advoi-staging`)  
**Live:** https://advoi.keyteller.com (`/var/www/advoi/live` · legacy `/opt/advoi` until cutover)

Human E2E does **not** block development. Track device tests in [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md) and formal Path A sign-off in [E2E-SIGNOFF.md](E2E-SIGNOFF.md).

**Related:** [DEVELOPMENT-MILESTONES.md](../current-state/DEVELOPMENT-MILESTONES.md) | [gaps-and-blockers.md](../current-state/gaps-and-blockers.md) | [improvement-roadmap.md](../current-state/improvement-roadmap.md) | [PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md) (holistic strategy)

---

## Baseline (shipped)

| Area | Status | Proof |
|------|--------|-------|
| 6-agent control plane | Done | `POST /api/agents/run-six`, 6 Docker daemons |
| Voice operator intents | Done | capabilities, run all, stop/restart, fleet, GitHub |
| Guardian fleet confirmation | Done | Two-turn confirm for high-risk fleet/dev actions |
| fm-bridge voice wiring | Done | `wake firstmate`, `start development`, `run next backlog` |
| Ingestion MVP | Done | `/ingest`, `/api/ingestion/*` |
| Squad dispatch (mock) | Done | 4 squads + `dispatch_squads=true` |
| Dashboard MVP | Done | `/dashboard` squad graph + run controls |
| PWA state machine + latency + recovery | Done (T0) | `3de87ac` `82b1375` `2c63897` — human A11–A13 open |
| PWA beacon → PEL | Done (T0) | `POST /api/events` @ `3b7df6c` |
| PWA interaction slice (wave 3) | Done (T0) | Gate chip `6c01c1c` · confirm parity `1689a33` · onboarding `e52898c` · home briefs `7f8bf47` — human A14–A17 open |
| PEL analytics funnel doc | Done | `docs/operations/ANALYTICS-FUNNEL.md` @ `12b1ad8` |
| OTEL + guardian trace_id | Done (T0 code) | `697b897` — VPS apply parked |
| fm-bridge 60s idempotency | Done (T0) | `70ce1a3` |
| T2 post-deploy smoke script | Done | `8584da3` `scripts/t2-staging-smoke.sh` |
| Aether proactive schema | Done (T0) | `ce6a8e2` |
| Aether Queued slice (feed skip / atomic publish / gate export) | Done (T0) | `686fe38` `8abbadd` `e71607f` — VPS cron parked (SSH) |
| Vertical boundaries architecture | Done | `6f29565` `docs/architecture/06-vertical-boundaries.md` |
| Guardian write-path hard-gate (fm-bridge) | Done (T0) | `61de279` ADR-028 · [audit](../../data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md) |
| Automated tests | Done | **494** pytest collected |

---

## Validation tiers

Use the **lowest tier that proves the change**. Do not skip tiers when promoting to staging or recording sign-off.

| Tier | Name | When to run | Gate |
|------|------|-------------|------|
| **T0** | Unit / integration | Every code change, pre-commit | `uv run pytest tests/ -q` — 100% pass |
| **T1** | Local smoke | After T0, before push | `agents-smoke-test` against local API (`ADVOI_BASE_URL=http://127.0.0.1:8010`) |
| **T2** | Staging API smoke | After VPS deploy | `scripts/t2-staging-smoke.sh` (health agents=6 + aether/status); full gate: `staging-signoff-precheck` + appendix curls |
| **T3** | Human E2E | Before production voice claim | [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md) matrix + [E2E-SIGNOFF.md](E2E-SIGNOFF.md) |

### Tier rules

- **Docs-only changes:** T0 optional; VPS `git pull` only (no container rebuild).
- **API / Python changes:** T0 + T1 minimum; T2 after staging deploy.
- **PWA / voice UX changes:** T0 + T2; T3 for mic/TTS paths.
- **Fleet / Guardian / FirstMate bridge:** T0 + T2 fleet intent curls; T3 for device confirm flow.
- **Regression:** If T2 fails, do not start T3 until fixed and T2 passes again.

---

## Milestone checklist

### M1 — Staging deploy parity (P0)

**Goal:** Staging matches `master` with full 6-frame PWA and operator bar.

| # | Task | Tier | Status |
|---|------|------|--------|
| M1.1 | `git pull --ff-only` on VPS `/var/www/advoi/staging` (or promote from develop) | — | [x] Done @ `5d50805` on advoi-staging |
| M1.2 | `bash /var/www/advoi/deploy-staging.sh` when code/images change | T2 | [x] Done |
| M1.3 | 6 frame buttons + operator bar on PWA | T2/T3 | [x] Done |
| M1.4 | `/api/aether/status` returns 200 | T2 | [x] Verified 2026-07-10 (HTTP 200, gate pass on VPS) |
| M1.5 | `agents-smoke` + `voice-smoke` pass on staging | T2 | [x] Verified 2026-07-10 (`staging-signoff-precheck.sh` exit 0) |

**Closes:** BUG-005, BUG-006, BUG-007 (deploy drift and operator fixes).

---

### M2 — Human voice sign-off (P0)

**Goal:** Recorded PASS for real mic + TTS on at least one path.

| # | Task | Tier | Status |
|---|------|------|--------|
| M2.1 | Path C `/voice-server` spot check (no WebGPU) | T3 | [ ] Open |
| M2.2 | Path A staging: Connect, greeting TTS within ~10s | T3 | [ ] Open |
| M2.3 | Tap frames A–F or say fleet/briefs/pulse intents | T3 | [ ] Open |
| M2.4 | Two-turn confirm: "queue review" then "yes" | T3 | [ ] Open |
| M2.5 | Operator: "what can you do", "run all agents" | T3 | [ ] Open |
| M2.6 | Fleet voice: "fleet status" with spoken backlog summary | T3 | [ ] Open |
| M2.7 | Copy results to [E2E-SIGNOFF.md](E2E-SIGNOFF.md) | T3 | [ ] Open |

**15-minute session:** See [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md#quick-manual-session-15-min).

---

### M3 — Voice hardening (P1)

**Goal:** Lower latency risk and broader device coverage.

| # | Task | Tier | Status |
|---|------|------|--------|
| M3.1 | `run_six_ms` in `/api/diagnostics/latency` | T0/T2 | [x] Done |
| M3.2 | Voice operator + fleet confirm tests | T0 | [x] Done |
| M3.3 | Path B WebGPU matrix (desktop + iOS Safari) | T3 | [ ] Open |
| M3.4 | Full mic → STT → TTS round-trip baseline | T2/T3 | [ ] Open — PWA SLA latency chip shipped (`82b1375`); human baseline still open |
| M3.5 | Playwright PWA connect smoke (no mic) | T0/T1 | [~] **Partial** — e2e stubs for state/latency/recovery/gate/confirm/onboarding/briefs; full connect smoke open |
| M3.6 | Guardian fleet confirm on device | T3 | [ ] Open — confirm **parity** T0 Done (`1689a33`, A15); device confirm still open |
| M3.7 | Explicit UI state machine (idle→…→error) | T0/T3 | [x] T0 Done (`3de87ac`); T3 A11 open |
| M3.8 | Error recovery paths (mic / LiveKit / API 502) | T0/T3 | [x] T0 Done (`2c63897`); T3 A13 open |
| M3.9 | Aether gate chip on home/dashboard | T0/T3 | [x] T0 Done (`6c01c1c`); T3 A14 open |
| M3.10 | Install strip + 60s morning pulse CTA | T0/T3 | [x] T0 Done (`e52898c`); T3 A16 open |
| M3.11 | Open briefs + review queue on home | T0/T3 | [x] T0 Done (`7f8bf47`…`587385d`); T3 A17 open |

**Wave 3 note:** PWA interaction Queued slice (M3.6 parity model + M3.9–M3.11 + funnel doc) is **T0 complete** on develop `587385d`. Staging promote + human A14–A17 remain open.

---

### M4 — Memory + observability (P2)

**Goal:** Operational memory and traces on VPS, not just code paths.

| # | Task | Tier | Status |
|---|------|------|--------|
| M4.1 | Operational memory retain on run-six | T0 | [x] Done |
| M4.2 | `GET /api/diagnostics/platform` | T2 | [x] Done |
| M4.3 | Letta client + JSONL fallback | T0 | [x] Done |
| M4.4 | `LETTA_ENABLED=true` on VPS + verify recall | T2 | [ ] Open |
| M4.5 | `OTEL_ENABLED=true` + collector sidecar | T2 | [~] **Code** on develop @ `697b897`; **VPS apply parked** (SSH host key; staging still `5d50805`) — verify `otel_ready` post-redeploy |
| M4.6 | Trace IDs in guardian events | T0/T2 | [~] **T0 Done** (`test_guardian_trace_id.py`); staging guardian log tail **parked** until promote |

---

### M5 — Live squad bridge (P2)

**Goal:** Real FirstMate/Discord dispatch instead of mock.

| # | Task | Tier | Status |
|---|------|------|--------|
| M5.1 | Squad registry (4 squads) | T0 | [x] Done |
| M5.2 | `dispatch_squads` + run-six integration | T0/T2 | [x] Done |
| M5.3 | Voice "dispatch all squads" | T0 | [x] Done |
| M5.4 | Live webhook URL on VPS | T2 | [ ] Open |
| M5.5 | `ADVOI_SQUAD_MOCK=false` on staging | T2 | [ ] Open |
| M5.6 | Discord crew ACK visible in fleet read | T3 | [ ] Open |

---

### M6 — Dashboard + visualization (P3)

| # | Task | Tier | Status |
|---|------|------|--------|
| M6.1 | `/dashboard` MVP (squad graph, run 6, dispatch) | T2 | [x] Done |
| M6.2 | React Flow interactive graph | T0/T3 | [ ] Open |
| M6.3 | Live agent freshness on graph | T2 | [ ] Open |

---

### M7 — Ingestion Phase 2 (P2)

**Goal:** Upload → triage → route → approve → FirstMate (no auto-dispatch on upload).

See [advoi/ingestion/README.md](../../advoi/ingestion/README.md).

| # | Task | Tier | Status |
|---|------|------|--------|
| M7.1 | Ingestion MVP (upload, route, optional dispatch-dev) | T0/T2 | [x] Done |
| M7.2 | `triage.py` classify + `needs_review` | T0 | [~] **Partial** — `triage_item` / `mark_needs_review` in pipeline + lifecycle API (`80b69fa`); no standalone `triage.py` classifier yet (**unchanged in wave 3**) |
| M7.3 | Status lifecycle: uploaded → triaged → routed → approved → dispatched | T0 | [~] **Partial** — happy path `uploaded → triaged → needs_review → approved → dispatched` + legacy `routed` (`80b69fa`, `tests/test_ingestion_lifecycle.py`); inbox UI / batch / voice still open (**unchanged in wave 3**) |
| M7.4 | Batch / folder upload endpoint | T0/T2 | [ ] Open |
| M7.5 | Triage inbox UI on `/ingest` | T3 | [ ] Open — home briefs/review surface is **not** ingestion triage inbox |
| M7.6 | Voice: "triage uploads", "route ingestion to {project}" | T0/T3 | [ ] Open |
| M7.7 | Guardian gate on batch approve + dispatch | T0 | [ ] Open |

**M7 note (wave 3):** No ingestion Phase 2 work in this batch. PWA home review queue (A17) surfaces deep-review briefs only — does not close M7.5.

---

### M8 — FirstMate Discord bridge (external)

**Goal:** Voice and PWA can read fleet backlog and trigger work with Guardian confirm.

| # | Task | Tier | Status |
|---|------|------|--------|
| M8.1 | `fm-bridge.sh` wired for wake/dev/backlog intents | T0 | [x] Done |
| M8.2 | `evaluate_fleet_confirmation` for high-risk actions | T0 | [x] Done |
| M8.3 | VPS fleet data path `/opt/firstmate-fleet/data/` | — | [x] Runtime only |
| M8.4 | Discord reply workflow (ACK / PROMOTE / NEXT) documented | — | [ ] Open |
| M8.5 | Fleet briefs committed or synced to GitHub | — | [ ] Open |
| M8.6 | 60s idempotency key on fm-bridge invoke | T0 | [x] Done (`70ce1a3`, `tests/test_fleet_idempotency.py`) |
| M8.7 | Guardian hard-gate on all live `invoke_fleet_trigger` paths | T0 | [x] Done (`61de279`, ADR-028, `tests/test_write_path_audit.py`) |
| M8.8 | Aether feed cron skips publish when gate FAIL (`FM_AETHER_GATE_REQUIRED`) | T0 | [x] Done (`686fe38`); VPS cron wire parked |
| M8.9 | Atomic publish gate + proactive + directives to fleet tree | T0 | [x] Done (`8abbadd`) |

**M8 note (wave 4):** Write-path audit closed P0 bare-invoke leaks. Deferred: voice→fleet import thinning (audit V4), aether fleet-tree publish vs strict vertical rule (V5).

---

### M9 — Portfolio ops (P3 / external)

| # | Task | Tier | Status |
|---|------|------|--------|
| M9.1 | Port registry → vps-shared | — | [ ] Open |
| M9.2 | clapart `develop` promote to staging (fleet backlog) | T2 | [ ] Open |
| M9.3 | Delete confirmed stale `fm/*` branches on GitHub (5 remain) | — | [ ] Open |
| M9.4 | Architecture docs 03/05 updated to 6 agents | — | [ ] Open |

---

### M10 — Portfolio Event Log / moat R1 (PEL)

**Goal:** Append-only `portfolio_events` is the control-plane event authority; fleet/frame/voice emits are observable.

| # | Task | Tier | Status |
|---|------|------|--------|
| M10.1 | Schema migration `deploy/migrations/001_portfolio_events.sql` + `append_event` | T0 | [x] Done (`advoi-analytics-pel-schema-01` @ `7682b96`) |
| M10.2 | Emit: `frame_run`, `fleet_trigger` (+ confirmation gate), `voice_intent` | T0 | [x] Done — `tests/test_portfolio_events.py` |
| M10.3 | Do **not** drop `memory_events` yet (deprecation checklist only) | — | [x] Documented in migration-plan |
| M10.4 | Staging: fleet trigger / frame run creates ≥1 `portfolio_events` row | **T2** | [ ] Open — develop `2b9a28e` not on staging (`5d50805`); **SSH promote parked** |
| M10.5 | `/api/events` ingest + optional query / `last_dispatch_at` from PEL | T0/T2 | [~] **Partial** — PWA thin beacon `POST /api/events` → PEL (`3b7df6c` T0); funnel stage SQL documented (`12b1ad8`); query/read API still open |
| M10.6 | Analytics funnel doc (connect → frame → confirm → success) | Docs | [x] Done (`docs/operations/ANALYTICS-FUNNEL.md` @ `12b1ad8`) |
| M10.7 | Aether gate snapshot export → repo path and/or PEL | T0 | [x] Done (`e71607f` — `governance_decision` / `gate_snapshot`); VPS cron + T2 parked |

**PEL note (batch 2026-07-10 wave 1):** Moat R1 code+design landed on develop at `7682b96`. Authority decision recorded as **ADR-027** (see also [07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md)).

**PEL / analytics note (wave 2):** Client beacon write path extends ADR-027 at `3b7df6c`. Next gates remain **M10.4** staging row proof + promote, then optional query API. Do not start dual-authority consumers until T2 passes.

**PEL / funnel note (wave 3):** Funnel SQL stages documented for ops/debug; live stage counts still require promote + traffic. Confirm parity ships `confirm_shown` / `confirm_accept` beacons (A15).

**PEL / gate export note (wave 4):** Nightly/post-gate export writes `data/aether/aether-gate-latest.md` and appends PEL gate_snapshot (`e71607f`). Staging proof still requires promote (M10.4).

**Design:** [07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md) · [migration-plan](../../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md) · ADR-027

**T2 gate (M10.4):** On staging Postgres after a confirmed fleet trigger or frame run:

```sql
SELECT source, type, venture_id, guardian_status, created_at
FROM portfolio_events
ORDER BY created_at DESC
LIMIT 10;
-- Expect: type IN ('fleet_trigger','frame_run','voice_intent','guardian_gate')
```

---

## Recommended sequence

```
M2 human E2E (parallel, not blocking)
    ↓
M4 Letta + OTel on VPS
    ↓
M5 live squad webhooks
    ↓
M7 ingestion Phase 2 triage
    ↓
M6 React Flow + M9 portfolio ops
```

M1 is **done** for current baseline. Re-run M1 checklist on every code deploy.

---

## Gap register

| ID | Priority | Item | Status |
|----|----------|------|--------|
| GAP-001 | P0 | Human E2E voice sign-off | **Open** |
| GAP-002 | P0 | Staging 6-frame deploy parity | **Done** @ `5d50805` (T2: 6/6 agents, precheck pass 2026-07-10) |
| GAP-003 | P1 | Path B iOS WebGPU / Kokoro load | Open (Path C fallback) |
| GAP-004 | P1 | Full mic latency human baseline | Open (T2 API: `sla_ok=false`, api_voice_path ~1.2–6.9s vs 800ms target) |
| GAP-005 | P1 | Fleet Guardian confirm on device | API done; human open |
| GAP-006 | P2 | `LETTA_ENABLED=true` on VPS | Open |
| GAP-007 | P2 | `OTEL_ENABLED=true` on VPS | **Partial** — code @ `697b897`; VPS apply parked (SSH) |
| GAP-008 | P2 | Live squad webhooks | Open |
| GAP-009 | P2 | Ingestion Phase 2 triage pipeline | **Partial** — lifecycle T0 @ `80b69fa`; classifier polish + UI open |
| GAP-010 | P3 | React Flow dashboard | Open |
| GAP-011 | P3 | Port registry / vps-shared | Open |
| GAP-012 | P3 | Architecture docs 03/05 (3-agent stale) | Open |
| GAP-013 | P0 ops | Staging promote develop→staging (SSH host key) | **Parked** — staging `5d50805` vs develop `2b9a28e` |
| GAP-014 | P1 | PWA human A11–A17 (state / latency / recovery / gate / confirm / install / briefs) | Open — T0 automated wave 2+3; T3 device |
| GAP-015 | P1 arch | Write-path V4 voice→fleet import thinning | Open — deferred wave 4 audit |
| GAP-016 | P2 arch | Aether fleet-tree publish vs vertical “no write” wording (audit V5) | Open — intentional publish; revisit rules |

### Bug cross-reference

| Bug | Roadmap | Notes |
|-----|---------|-------|
| BUG-005 | M1 | **Closed** — staging redeployed |
| BUG-006 | M1/M2 | **Closed in code** — verify in M2 T3 |
| BUG-007 | M1/M2 | **Closed in code** — verify in M2 T3 |
| BUG-001/004 | M3 | Mitigated via Path C |

---

## Definition of "production voice ready"

1. [x] Code: 6 agents, 3 voice paths, operators, squads, ingestion MVP, fm-bridge (Guardian hard-gate ADR-028), PWA interaction shell, Aether Queued slice (feed/publish/export), PEL + beacon + funnel doc
2. [x] T0: 494 pytest collected; wave4 suites 105 passed (wave3 61; wave2 83 prior)
3. [~] T2: bootstrap smoke pass @ `5d50805` (precheck + t2-smoke 2026-07-10); **re-promote + tip re-smoke parked** (GAP-013) — post-deploy script ready `8584da3`
4. [ ] T3: Human Path A or C sign-off recorded (include A11–A17)
5. [ ] T2: Letta/OTel enabled on VPS
6. [ ] T2: Live squad webhooks (non-mock)

---

## Appendix — validation commands

### T0 — pytest (local)

```bash
cd advoi-system
uv sync
uv run pytest tests/ -q
```

Target suites after fleet/voice changes:

```bash
uv run pytest tests/test_voice_intent.py tests/test_guardian.py tests/test_fleet_bridge.py -q
```

### T1 — local API smoke

```powershell
# Windows — start stack first (run-multi-agent-stack.ps1 -WithRedis)
.\scripts\agents-smoke-test.ps1
$env:ADVOI_BASE_URL = "http://127.0.0.1:8010"
.\scripts\voice-smoke-test.ps1
```

```bash
# Bash / WSL
ADVOI_BASE_URL=http://127.0.0.1:8010 bash scripts/agents-smoke-test.sh
ADVOI_BASE_URL=http://127.0.0.1:8010 bash scripts/voice-smoke-test.sh
```

### T2 — staging smoke

**Scope reminder:** A green T2 on the public staging URL proves the **currently deployed** VPS tree (today: bootstrap `5d50805`). It does **not** prove develop tip (`2b9a28e`) until promote lands (GAP-013).

**Minimum post-deploy job** (non-zero exit on failure; also run by `staging-redeploy.sh`):

```bash
# Default: https://advoi-staging.keyteller.com
bash scripts/t2-staging-smoke.sh

# Live host only when intentionally checking production-facing cutover:
ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/t2-staging-smoke.sh

# T0 offline parse check
bash scripts/t2-staging-smoke.sh --fixture-dir tests/fixtures/t2-smoke
uv run pytest tests/test_t2_staging_smoke.py -q
```

Full pre-human gate:

```bash
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh
```

```powershell
.\scripts\staging-signoff-precheck.ps1
```

#### T2 — targeted API checks

```bash
BASE="${ADVOI_BASE_URL:-https://advoi-staging.keyteller.com}"

# Health + agents (expect 6 ready) — or use scripts/t2-staging-smoke.sh
curl -sf "$BASE/api/health"
curl -sf "$BASE/api/agents" | python3 -m json.tool

# Run-six
curl -sf -X POST "$BASE/api/agents/run-six?refresh=true"

# Voice intent (operator preview, no auto-confirm)
curl -sf -X POST -H "Content-Type: application/json" \
  -d '{"transcript":"run all agents"}' "$BASE/api/voice/intent"

# Fleet trigger preview (Guardian gate — use valid action, not frame id)
curl -sf -X POST -H "Content-Type: application/json" \
  -d '{"action":"wake_firstmate","confirmed":false}' "$BASE/api/fleet/trigger"

# Platform diagnostics
curl -sf "$BASE/api/diagnostics/platform"
curl -sf "$BASE/api/diagnostics/latency"
curl -sf "$BASE/api/diagnostics/guardian"

# Ingestion summary
curl -sf "$BASE/api/ingestion/summary"

# Aether
curl -sf "$BASE/api/aether/status"

# PEL emit smoke (M10.4) — confirmed fleet trigger should append portfolio_events
curl -sf -X POST -H "Content-Type: application/json" \
  -d '{"action":"wake_firstmate","confirmed":true,"project":"clapart"}' \
  "$BASE/api/fleet/trigger"
# Then on VPS Postgres: SELECT type, source, venture_id FROM portfolio_events
#   ORDER BY created_at DESC LIMIT 5;
# Expect ≥1 row with type=fleet_trigger (and/or guardian_gate from confirm path)
```

### T2 — VPS deploy (when code or images change)

```bash
ssh deploy@187.77.140.216
bash /var/www/advoi/promote-to-staging.sh
# or: bash /var/www/advoi/deploy-staging.sh
# Minimum T2 (also run by staging-redeploy.sh):
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/t2-staging-smoke.sh
# Full pre-human gate:
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh
```

Docs-only deploy:

```bash
ssh deploy@187.77.140.216 "cd /var/www/advoi/staging && git pull --ff-only"
```

### T3 — human E2E

1. Open https://advoi-staging.keyteller.com (Path A) or `/voice-server` (Path C).
2. Run rows A1–A9 or C1–C5 in [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md).
3. Record PASS/FAIL in [E2E-SIGNOFF.md](E2E-SIGNOFF.md).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Initial roadmap: validation tiers T0–T3, milestones M1–M9, gap register, appendix commands. Baseline `71fd7ae`, staging 6/6. |
| 2026-07-10 | www staging tier: `advoi-staging.keyteller.com`, `/var/www/advoi/staging`, T2 commands updated. |
| 2026-07-10 | T2 validation run: precheck pass, M1.4 aether 200, appendix fleet curl fixed; baseline SHA `5d50805`. |
| 2026-07-10 | M10 PEL schema + emit T0; cross-link T2 M10.4 staging row check (`advoi-analytics-pel-schema-01`). |
| 2026-07-10 | T2 post-deploy job: `scripts/t2-staging-smoke.sh` + `t2_validate.py` (health agents=6, aether/status); fixture T0 tests; wired into `staging-redeploy.sh`. Default host `advoi-staging.keyteller.com`. |
| 2026-07-10 | **Wave 2 wrap-up:** PWA state/latency/recovery (M3.7–M3.8), OTEL+trace_id code (M4.5–M4.6), beacon POST (M10.5 partial), fm-bridge idempotency (M8.6), aether proactive schema T0; develop `ce6a8e2`; **SSH promote parked** (GAP-013). |
| 2026-07-10 | **Wave 3 wrap-up:** PWA interaction slice complete — gate chip (M3.9), confirm parity (M3.6 model), onboarding (M3.10), home briefs (M3.11), funnel doc (M10.6); M7 unchanged; develop `587385d`; **SSH promote parked** (GAP-013). |
| 2026-07-10 | **Wave 4 wrap-up:** Aether Queued complete — feed skip (M8.8), atomic publish (M8.9), gate export (M10.7); Guardian write-path hard-gate (M8.7, ADR-028); vertical boundaries doc; develop `61de279`; **SSH promote parked** (GAP-013). |
| 2026-07-10 | **Ops review:** live T2 re-verified @ advoi-staging (bootstrap `5d50805`); develop tip was `3d5a00d`; docs corrected — T2 pass ≠ tip parity; GAP-013 still parked. |
| 2026-07-10 | **Batch roadmap sync:** tip SHA → `2b9a28e` (decision-sync after ops-review); GAP-013 / M10.4 / T2 scope still bootstrap-only; no milestone checkbox flips (align table hold). |
