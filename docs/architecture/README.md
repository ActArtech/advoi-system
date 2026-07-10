# Architecture documentation

System design for ADVoi as implemented in `advoi-system/`. These docs describe **what is built**, how components connect, and where intelligence lives.

| Doc | Topic |
|-----|-------|
| [01-system-overview.md](01-system-overview.md) | Verticals, horizontals, repo layout |
| [02-voice-paths.md](02-voice-paths.md) | LiveKit Path A (incl. home briefs surface) vs client Path B |
| [03-multi-agent.md](03-multi-agent.md) | Specialist agents, frames, daemons |
| [04-memory-and-data.md](04-memory-and-data.md) | Hindsight, Postgres, Redis, bridge; **data authority matrix** (canonical source per entity) |
| [05-deployment-topology.md](05-deployment-topology.md) | Docker services, VPS, networking |
| [06-vertical-boundaries.md](06-vertical-boundaries.md) | Dependency diagram + import/write rules per vertical |
| [07-portfolio-event-log.md](07-portfolio-event-log.md) | PEL schema (`portfolio_events`), `memory_events` mapping, emit points |
| [08-system-logic-flows.md](08-system-logic-flows.md) | Mermaid: voice, ingest, fleet bridge, memory retain, Aether gate |

## Related (existing)

- [../MEMORY-STACK.md](../MEMORY-STACK.md) — operator setup for memory tiers
- [../CLARITY-FRAMEWORK.md](../CLARITY-FRAMEWORK.md) — product vision and ontology
- [../decision-log/DECISION-LOG.md](../decision-log/DECISION-LOG.md) — ADRs
- [../reviews/PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md) — moat R1 PEL foundation
- [../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md) — data/memory/vertical review; § System logic source for [08](08-system-logic-flows.md)
- [../../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md](../../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md) — one-table authority + migration steps

## Stage

**Current:** Build 1.5+ — Voice + PWA + **6** multi-agent frames (A–F); Aether / Guardian / Squads / Ingestion **Built** (see [01-system-overview.md](01-system-overview.md)). Ahead of `.aether/STAGE.md` 1.1 checklist; see [../current-state/gaps-and-blockers.md](../current-state/gaps-and-blockers.md). Doc sync `fm/advoi-arch-doc-sync-01` closes arch review *Routing/Decision Stale* ([ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md)).