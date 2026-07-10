# Alignment log

**Purpose:** After each good batch, record alignment between runtime, Aether gate, fleet, roadmap, moat strategy, and architecture docs.

**Process:** See [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)

**Related:** [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md) · [PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md) · [ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md)

---

## Index

| Date | Batch | Gate | Staging SHA | Misalignments |
|------|-------|------|-------------|---------------|
| 2026-07-10 | wave 3 PWA interaction | hold (SSH promote) | `5d50805` (bootstrap) | develop `587385d` ahead; PWA A14–A17 T3 + PEL T2 parked |
| 2026-07-10 | wave 2 PWA/analytics/aether | hold (SSH promote) | `5d50805` (bootstrap) | develop `ce6a8e2` ahead; OTEL/PEL T2 parked |
| 2026-07-10 | AFK arch wave + PEL | hold (promote open) | `5d50805` (bootstrap) | develop `7682b96` ahead of staging; PEL T2 open |

---

## Template (copy per batch)

```markdown
## [YYYY-MM-DD] — <batch title>

| Check | Status | Evidence |
|-------|--------|----------|
| Aether gate | | |
| Fleet active_slug | advoi | |
| ROADMAP milestones | | |
| Moat R1-R10 touch | | |
| Architecture doc drift | | |
| Staging smoke | | |

**Misalignments:** 
**Follow-up IDs:** 
```

---

_Add entries below newest first._

## [2026-07-10] — wave 3 PWA interaction slice (batch wrap-up)

| Check | Status | Evidence |
|-------|--------|----------|
| Aether gate | improved (PWA surface) | Gate chip on home/dashboard from `GET /api/aether/status` (`6c01c1c`); proactive schema still T0-only until promote |
| Fleet `active_slug` | advoi | Shown on gate chip when present; fm-bridge idempotency still wave2 |
| ROADMAP-VALIDATION milestones | PWA interaction complete (T0) | **M3** UX shell + A14–A17 T0; **M7** unchanged; **M10** funnel docs extend write-path analytics; M2 human open |
| PORTFOLIO-SYSTEM-MOAT R1–R10 | R1 surface + funnel | Confirm beacons + funnel SQL (`12b1ad8`); home briefs thin read (no dual PEL authority) |
| BATCH-DOCUMENTATION gate | honored | 5 Queued Done since `727f77f` + milestone (PWA interaction complete) → wrap-up before resume |
| Staging smoke | hold | Tip not on staging; SSH promote still parked |
| Drift: develop vs staging | increased | develop `587385d` vs staging `5d50805` |

**Misalignments found:** SSH promote still blocks all staging proof of wave 2+3 code. Path A product shell is complete in repo but not on VPS. M7 Phase 2 deliberately not advanced — no drift, intentional deferral.  
**Follow-up backlog IDs:** OPP-002 (SSH + promote); OPP-001 human A14–A17; OPP-003 funnel T2; OPP-007 M7 Phase 2; M10.4 PEL rows.

**Discipline:** No new ADR (see DECISION-LOG batch notes). Evidence: `data/feedback-evidence/batch-2026-07-10-wave3/summary.md`. Status of wrap-up: **Partial** until promote unblocked. **Milestone:** PWA interaction Queued slice complete.

## [2026-07-10] — wave 2 PWA / analytics / aether (batch wrap-up)

| Check | Status | Evidence |
|-------|--------|----------|
| Aether gate | improved (code) | Proactive feed JSON Schema + T0 gate validator `ce6a8e2`; live VPS feed still needs promote |
| Fleet `active_slug` | advoi | fm-bridge 60s idempotency `70ce1a3` (T0) |
| ROADMAP-VALIDATION milestones | partial advance | **M3** state/latency/recovery T0; **M3.5** stubs; **M4.5–M4.6** T0 code; **M8** idempotency; **M10.5** write path (beacon); M7 unchanged this wave |
| PORTFOLIO-SYSTEM-MOAT R1–R10 | R1 + R6 | PWA beacon → PEL (R1); OTEL + guardian `trace_id` (R6) |
| BATCH-DOCUMENTATION gate | honored | 8 Done since `b2ced10` → wrap-up before resume Queued |
| Staging smoke | hold | T2 script + CI ready `8584da3`; live T2 re-run blocked by SSH promote |
| Drift: develop vs staging | increased | develop `ce6a8e2` vs staging `5d50805` |

**Misalignments found:** SSH host key verification failed — cannot promote develop or apply OTEL on staging. Staging still bootstrap-era code; PEL M10.4, beacon T2, and `otel_ready` unproven on VPS.  
**Follow-up backlog IDs:** OPP-006 (SSH + promote); OPP-002 (OTEL T2); M10.4 PEL rows; M2 human A11–A13; OPP-007 proactive feed live.

**Discipline:** No new ADR (beacon extends ADR-027). Evidence: `data/feedback-evidence/batch-2026-07-10-wave2/summary.md`. Status of wrap-up: **Partial** until promote unblocked.

## [2026-07-10] — AFK architecture wave + PEL milestone

| Check | Status | Evidence |
|-------|--------|----------|
| Aether gate (`/api/aether/status`) | hold | Bootstrap feed path `a7c6d78`; full gate PASS still needs live feed JSON on VPS |
| Fleet `active_slug` | advoi | fleet-profile / www bootstrap batch |
| ROADMAP-VALIDATION milestones | partial | **M7.2/M7.3** partial (lifecycle T0); **M10.1–M10.3** done @ `7682b96`; M10.4 open |
| PORTFOLIO-SYSTEM-MOAT R1–R10 | R1 advanced | PEL schema + emit (moat R1); ingestion lifecycle advances R4 |
| ARCHITECTURE-DATA-MEMORY-REVIEW | improved | retain audit + brief triple-path + PEL design closed queue items |
| Staging URL | advoi-staging.keyteller.com | health / T2 precheck pass @ bootstrap `5d50805` |
| Drift: architecture docs | reduced | `e8a0387` overview + multi-agent → 6 agents; 05 topology may still lag |
| Arch review intake | closed queue | `advoi-arch-review-01` ships landed on develop |

**Misalignments found:** develop tip `7682b96` not yet on staging; PEL rows not proven on VPS Postgres; Letta/OTel still off; squads still mock.  
**Follow-up backlog IDs:** staging promote + M10.4; M2 human E2E; optional M7.4+; deferred OPP for PWA/OTel/live webhooks.
