# Batch wrap-up — AFK wave 2026-07-10 (8+ Done, PEL milestone)

**Batch:** Architecture + memory + ingestion + PEL schema wave  
**Captain:** First Mate AFK continuous loop  
**Status:** Complete (docs wrap-up on branch `fm/advoi-batch-wrapup-template-01`)  
**Develop tip:** `7682b96` — Portfolio Event Log schema and emit paths (moat R1)

## Done items this wave (8+)

| ID / theme | SHA | Notes |
|------------|-----|-------|
| Batch documentation standard | `b099e99` | DEV/DECISION/OPP/ALIGNMENT wrap-up process |
| Aether docs feed bootstrap | `a7c6d78` | `docs/aether` path for fm-aether-gate |
| Arch doc reconcile (6 agents) | `e8a0387` | overview + multi-agent docs |
| ADR-026 retain audit + MemoryRouter | `6f3f232` | retain integrity inventory |
| Brief Curator PG-canonical | `89e5556` | Redis cache-only (ADR-026) |
| Ingestion lifecycle M7.2–M7.3 | `80b69fa` | uploaded→…→dispatched; T0 tests |
| Ontology vocabulary registry | `32c75e9` | frames, agents, ventures |
| PEL design + migration plan | `c91e921` | `07-portfolio-event-log.md` |
| PEL schema + emit (moat R1) | `7682b96` | `append_event`, frame/fleet/voice emits |

Related fleet evidence dirs: `advoi-arch-review-01`, `advoi-memory-retain-audit-01`, `advoi-data-memory-events-pel-01`, `advoi-roadmap-review-01`, `advoi-moat-review-01`.

## Summary

AFK wave closed multiple architecture-review ship queue items: memory retain audit, brief triple-path fix, ingestion lifecycle state machine, ontology registry, and **Portfolio Event Log (PEL)** as control-plane event authority (moat R1). Schema migration and minimum emit paths ship at `7682b96`. Staging still at older SHA for code promote; M10.4 T2 row verification open after deploy with `DATABASE_URL`.

## Staging smoke (bootstrap baseline)

- URL: https://advoi-staging.keyteller.com/api/health
- Bootstrap SHA: `5d50805` (pre-wave staging)
- T2 precheck: pass 2026-07-10 (`advoi-roadmap-review-01`)
- Develop HEAD for this wrap-up: `7682b96` (not yet promoted for PEL T2)

## Blockers parked

- M10.4: staging PEL row proof after promote + Postgres
- M2: human T3 voice E2E (device)
- M4.4/M4.5: Letta + OTel on VPS (deferred — OPP)
- M5.4/M5.5: live squad webhooks (deferred — OPP)
- M3.5: Playwright PWA smoke (deferred — OPP)

## Opportunities (see OPPORTUNITIES-LOG)

- PWA Playwright connect smoke
- OTel collector + `OTEL_ENABLED` on VPS
- Live squad webhooks (`ADVOI_SQUAD_MOCK=false`)
- Dedicated `triage.py` classifier polish beyond lifecycle API

## Next Queued slice

- Promote develop → staging; re-run T2; prove M10.4 PEL rows
- Human E2E (M2) when device available
- Optional: M7.4+ batch upload / inbox UI
