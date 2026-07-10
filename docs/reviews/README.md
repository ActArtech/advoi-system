# External reviews

| Document | Audience | Purpose |
|----------|----------|---------|
| [PORTFOLIO-SYSTEM-MOAT.md](PORTFOLIO-SYSTEM-MOAT.md) | Product, architecture, engineering leads | Holistic portfolio connections, shared state, moat thesis, cross-module recommendations |
| [EXTERNAL-ENGINEERING-ARCHITECTURE-REVIEW.md](EXTERNAL-ENGINEERING-ARCHITECTURE-REVIEW.md) | Senior engineers, architects, security reviewers | Full system pack for independent review |
| [ARCHITECTURE-DATA-MEMORY-REVIEW.md](ARCHITECTURE-DATA-MEMORY-REVIEW.md) | Architecture, data, platform | Vertical/horizontal map, data authority, ADR-026 gaps; source for [06-vertical-boundaries](../architecture/06-vertical-boundaries.md) |
| [../architecture/07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md) | Data, analytics, platform | PEL `portfolio_events` schema (moat R1); reconciles `memory_events` |
| [../../data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md](../../data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md) | Architecture, security | fm-bridge + fleet write-path audit: all live invokes through Guardian; T0 `tests/test_write_path_audit.py` |

**Start here** for third-party architecture assessment. For day-to-day ops, use `docs/current-state/SYSTEM-STATUS.md` instead.