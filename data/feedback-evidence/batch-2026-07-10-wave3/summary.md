# Batch wrap-up — wave 3 PWA interaction slice (2026-07-10)

**Batch:** PWA interaction Queued slice complete (home shell: gate chip, confirm parity, onboarding, briefs surface, funnel doc)  
**Captain:** First Mate (crewmate wrap-up `advoi-batch-wrapup-wave3-01`)  
**Status:** **Partial** — code complete on develop; staging VPS promote **parked** (SSH host key)  
**Develop tip:** `587385d`  
**Prior wrap-up:** `727f77f` (wave 2 @ `ce6a8e2`)  
**Staging SHA:** `5d50805` (unchanged — promote blocked)

## Done items this wave (5 Queued + no-mistakes lint)

| Theme | SHA | Notes |
|-------|-----|-------|
| Aether PWA gate chip | `6c01c1c` | `GET /api/aether/status` → home/dashboard chip (A14) |
| Confirm parity voice+tap | `1689a33` | Identical Guardian copy; Confirm button + beacons (A15) |
| PEL analytics funnel doc | `12b1ad8` | `docs/operations/ANALYTICS-FUNNEL.md` connect→success SQL |
| Install strip + morning pulse CTA | `e52898c` | Browser vs standalone + 60s pulse (A16) |
| Open briefs + review queue on home | `7f8bf47` (+ review/docs/lint) | Home cards; thin `GET /api/briefs` (A17); tip `587385d` |

Related no-mistakes trail on develop: `5a25014` `a365bf6` `fc3a8a1` `587385d` (briefs surface review + docs + Ruff/tsc).

## Milestone

**PWA interaction Queued slice complete** on develop. Path A home now carries: state/latency/recovery (wave 2) + gate chip + confirm parity + install/onboarding + briefs/review surface. Human A14–A17 remain device-side (T3).

## Smoke / T0

| Check | Result |
|-------|--------|
| Full pytest collection | **415** tests |
| Wave3 suite subset | **61 passed** (see `pytest-wave3.txt`) |
| Suites | `test_aether_gate_chip`, `test_confirm_parity`, `test_pwa_onboarding`, `test_pwa_briefs_surface`, `test_pwa_beacon_events` |
| Staging live T2 | **Not re-run** — SSH host key verification failed on promote |
| Bootstrap T2 (prior) | Pass 2026-07-10 @ staging `5d50805` |

## Blockers parked

1. **Staging VPS promote** — SSH host key verification failed  
   - Staging remains @ `5d50805`  
   - Develop @ `587385d`  
   - Blocks: M1 re-parity, M4.5–M4.6 OTEL T2, M10.4 PEL rows, beacon/funnel T2, A14–A17 on real staging tip  
2. **M2 human E2E** — still open (device); now includes A11–A17  
3. **M5 live webhooks / M4.4 Letta / M7 Phase 2** — deferred (OPP), not wave3 scope

## Decisions

- **No new ADR.** Gate chip / confirm parity / onboarding / home briefs are PWA product surfaces under ADR-001/002/012. Thin `GET /api/briefs` reuses Brief Curator path (ADR-026). Funnel queries document ADR-027 PEL beacons.

## Logs updated

- `docs/dev-log/DEV-LOG.md` — wave 3 entry  
- `docs/decision-log/DECISION-LOG.md` — no ADR; batch note  
- `docs/current-state/OPPORTUNITIES-LOG.md` — wave 3 OPPs  
- `docs/current-state/ALIGNMENT-LOG.md` — wave 3 alignment  
- `docs/operations/ROADMAP-VALIDATION.md` — PWA baseline + M3/M7/M10 notes  
- `docs/current-state/gaps-and-blockers.md` — tip + A14–A17  

## Next Queued slice (after wrap-up merge)

1. Fix SSH known_hosts / host key for deploy host  
2. Promote develop → staging; `t2-staging-smoke.sh` + full precheck  
3. Prove M10.4 + funnel stages on staging Postgres; optional OTEL apply  
4. Human E2E M2 including A11–A17 when device available  
5. Resume Queued fleet dispatch  

## Resume condition

Mandatory BATCH-DOCUMENTATION artifacts present on branch `fm/advoi-batch-wrapup-wave3-01`. Firstmate merges to `develop` (no PR / VPS-direct). Queued dispatch may resume after merge.
