# Batch wrap-up — wave 4 Aether / system / arch slice (2026-07-10)

**Batch:** Aether Queued slice complete + Guardian write-path audit  
**Captain:** First Mate (crewmate wrap-up `advoi-batch-wrapup-wave4-01`)  
**Status:** **Partial** — code complete on develop; staging VPS promote **parked** (SSH host key)  
**Develop tip:** `61de279`  
**Prior wrap-up:** `ff74a98` (wave 3 @ `587385d`)  
**Staging SHA:** `5d50805` (unchanged — promote blocked)

## Done items this wave (5 Queued)

| Theme | SHA | Notes |
|-------|-----|-------|
| Gate-required feed skip | `686fe38` | `FM_AETHER_GATE_REQUIRED=1` → skip fleet feed on gate FAIL (exit ≥2); `scripts/aether-feed-cron.sh` |
| Atomic Aether publish | `8abbadd` | All-or-nothing gate + proactive + directives → `FIRSTMATE_FLEET_PATH` |
| Gate export repo + PEL | `e71607f` | `data/aether/aether-gate-latest.md` + `portfolio_events` governance_decision / gate_snapshot |
| Vertical boundaries doc | `6f29565` | `docs/architecture/06-vertical-boundaries.md` + ARCHITECTURE-DATA-MEMORY-REVIEW land |
| Guardian write-path hard-gate | `61de279` | P0 fm-bridge: require guardian token on invoke; remove free-form API path; harden ingestion |

## Milestone

**Aether Queued slice complete** on develop: feed cron respects gate, atomic multi-artifact publish, durable gate export (repo + PEL). **Guardian write-path audit** closed P0 leaks (V1 structural hard-gate, V2 dead API branch, V3 ingestion contract). Deferred: V4 voice→fleet import (P1), V5 aether fleet-tree publish tension (P2). Full audit: [advoi-arch-write-path-audit-01/audit.md](../advoi-arch-write-path-audit-01/audit.md).

## Smoke / T0

| Check | Result |
|-------|--------|
| Full pytest collection | **494** tests |
| Wave4 suite subset | **105 passed** (see `pytest-wave4.txt`) |
| Core suites | feed_cron, publish_atomic, gate_export, write_path_audit (**78**) + fleet_trigger + fleet_idempotency |
| Staging live T2 | **Not re-run** — SSH host key verification failed on promote |
| Bootstrap T2 (prior) | Pass 2026-07-10 @ staging `5d50805` |

## Blockers parked

1. **Staging VPS promote** — SSH host key verification failed  
   - Staging remains @ `5d50805`  
   - Develop @ `61de279`  
   - Blocks: M1 re-parity, M4.5–M4.6 OTEL T2, M10.4 PEL rows, gate-export PEL on VPS, A14–A17 on real staging tip, live aether feed cron  
2. **M2 human E2E** — still open (device); includes A11–A17  
3. **M5 live webhooks / M4.4 Letta / M7 Phase 2** — deferred (OPP), not wave4 scope

## Decisions

- **ADR-028** — Guardian hard-gate on all live `invoke_fleet_trigger` / fm-bridge paths (Accepted). Implements vertical-boundary write rules; convention alone was insufficient (P0).  
- Aether feed skip / atomic publish / gate export implement ADR-005 (Aether portfolio) + ADR-027 (PEL authority for gate_snapshot) without new ADRs beyond 028.

## Logs updated

- `docs/dev-log/DEV-LOG.md` — wave 4 entry  
- `docs/decision-log/DECISION-LOG.md` — ADR-028 + batch note  
- `docs/current-state/OPPORTUNITIES-LOG.md` — wave 4 OPPs  
- `docs/current-state/ALIGNMENT-LOG.md` — wave 4 alignment  
- `docs/operations/ROADMAP-VALIDATION.md` — Aether/Guardian baseline + M8/M10 notes  
- `docs/current-state/gaps-and-blockers.md` — tip + write-path  

## Next Queued slice (after wrap-up merge)

1. Fix SSH known_hosts / host key for deploy host  
2. Promote develop → staging; `t2-staging-smoke.sh` + full precheck  
3. Prove M10.4 + gate_export / funnel stages on staging Postgres; optional OTEL apply  
4. Wire aether feed cron + gate export cron on VPS when promote lands  
5. Human E2E M2 including A11–A17 when device available  
6. Optional: voice→fleet thin routing (audit V4); revisit aether fleet-tree publish vs vertical rules (V5)  
7. Resume Queued fleet dispatch  

## Resume condition

Mandatory BATCH-DOCUMENTATION artifacts present on branch `fm/advoi-batch-wrapup-wave4-01`. Firstmate merges to `develop` (no PR / VPS-direct). Queued dispatch may resume after merge.
