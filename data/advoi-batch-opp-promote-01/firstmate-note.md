# Firstmate note — advoi-batch-opp-promote-01

**Date:** 2026-07-10  
**Branch:** `fm/advoi-batch-opp-promote-01` (from `origin/develop` @ `741e961`)  
**Repo updates:** `docs/current-state/OPPORTUNITIES-LOG.md` + `docs/dev-log/DEV-LOG.md`  
**Crewmate does not write** `/data/backlog.md` — firstmate files the cards below.

## Gate

**PASS** — every open value≥7 OPP is either promoted (new id or mapped to existing Queued) or explicit deferred (complexity L) with rationale in OPPORTUNITIES-LOG.

## Promote → fleet `## Queued` (NEW — file these)

Add under an appropriate Queued section (recommend **Queued (ops + validation post-wave4)** or captain cutover):

```markdown
- [ ] advoi-ops-staging-promote-01 - Fix SSH known_hosts/host key + promote develop→staging; re-run t2-staging-smoke + precheck (repo: advoi, lane: OPS, value: 9, complexity: S, source: wave4 OPP-001 / GAP-013, gate: staging VPS SHA == develop tip + T2 exit 0, promote: captain)
- [ ] advoi-ops-aether-cron-wire-01 - After promote: install aether-feed-cron + gate-export on VPS (FM_AETHER_GATE_REQUIRED=1) (repo: advoi, lane: OPS, value: 8, complexity: S, source: wave4 OPP-002, depends: advoi-ops-staging-promote-01, gate: cron present + gate FAIL skips feed, promote: captain)
- [ ] advoi-val-pel-m10-4-proof-01 - After promote: prove M10.4 PEL rows + gate_snapshot + funnel SQL (connect→success) on staging Postgres (repo: advoi, lane: VAL, value: 8, complexity: S, source: wave4 OPP-003 + wave3 OPP-003, depends: advoi-ops-staging-promote-01, gate: logged SQL evidence in feedback-evidence, promote: yes)
```

**Suggested ship order after current in-flight closes:**  
1. `advoi-ops-staging-promote-01` (unblocks tip T2)  
2. parallel: `advoi-ops-aether-cron-wire-01` + `advoi-val-pel-m10-4-proof-01` + existing `advoi-roadmap-t2-m4-05` (OTEL apply)

## Already in fleet (MAP only — do not duplicate)

| OPP theme | Value | Existing backlog id | Status in backlog |
|-----------|-------|---------------------|-------------------|
| Human A11–A17 / T3 device E2E | 8 | `advoi-roadmap-t3-m2-01` | Queued, parked T3 |
| OTEL VPS apply M4.5/M4.6 | 8 | `advoi-roadmap-t2-m4-05` | Queued (captain) |
| Live squad webhooks M5.4/M5.5 | 7 | `advoi-roadmap-t2-m5-04` | Queued (captain) |
| M7.2 triage classifier (not Phase 2 UI) | 6–7 | `advoi-roadmap-m7-02` | Queued |

Optional: annotate those four rows with `opp-promote-01 mapped 2026-07-10` if useful for audit.

## Explicit deferred (value≥7, do **not** Queued as-is)

| Theme | Value | Cx | Rationale |
|-------|-------|----|-----------|
| M7 Phase 2 triage inbox UI + batch upload + voice triage | 7 | **L** | Above promote bar complexity; keep `advoi-roadmap-m7-02` for classifier only; split product surface later when lifecycle has staging traffic |

## Low-value left deferred (no new cards)

Write-path V4/V5 (6/5), Playwright full connect smoke M3.5 (6), live cutover (5), M10.5 PEL read API (5), aether live feed producer (6 — partially covered by cron wire). Full one-liners in `docs/current-state/OPPORTUNITIES-LOG.md` § opp-promote-01.

## Evidence / sources

- `docs/current-state/OPPORTUNITIES-LOG.md` (updated)
- `data/feedback-evidence/batch-2026-07-10-wave2/summary.md`
- `data/feedback-evidence/batch-2026-07-10-wave3/summary.md`
- `data/feedback-evidence/batch-2026-07-10-wave4/summary.md`
- Fleet snapshot reviewed: `/data/backlog.md` (Queued sections through arch/data)

## Merge note (VPS-direct)

Firstmate merges repo branch `fm/advoi-batch-opp-promote-01` → `develop` (no PR). Then file the three NEW Queued cards above into `/data/backlog.md` and mark `advoi-batch-opp-promote-01` Done.
