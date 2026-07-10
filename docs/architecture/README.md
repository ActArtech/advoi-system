# Architecture documentation

System design for ADVoi as implemented in `advoi-system/`. These docs describe **what is built**, how components connect, and where intelligence lives.

| Doc | Topic |
|-----|-------|
| [01-system-overview.md](01-system-overview.md) | Verticals, horizontals, repo layout |
| [02-voice-paths.md](02-voice-paths.md) | LiveKit server voice vs planned client voice |
| [03-multi-agent.md](03-multi-agent.md) | Specialist agents, frames, daemons |
| [04-memory-and-data.md](04-memory-and-data.md) | Hindsight, Postgres, Redis, bridge |
| [05-deployment-topology.md](05-deployment-topology.md) | Docker services, VPS, networking |

## Related (existing)

- [../MEMORY-STACK.md](../MEMORY-STACK.md) — operator setup for memory tiers
- [../CLARITY-FRAMEWORK.md](../CLARITY-FRAMEWORK.md) — product vision and ontology
- [../decision-log/DECISION-LOG.md](../decision-log/DECISION-LOG.md) — ADRs

## Stage

**Current:** Build 1.5+ — Voice + PWA + **6** multi-agent frames (A–F); Aether / Guardian / Squads / Ingestion **Built** (see [01-system-overview.md](01-system-overview.md)). Ahead of `.aether/STAGE.md` 1.1 checklist; see [../current-state/gaps-and-blockers.md](../current-state/gaps-and-blockers.md). Doc sync `fm/advoi-arch-doc-sync-01` closes arch review *Routing/Decision Stale* ([ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md)).