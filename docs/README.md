# ADVoi documentation

**Start here:** [current-state/SYSTEM-STATUS.md](current-state/SYSTEM-STATUS.md) for honest build status (2026-07-10).

## Documentation map

```
docs/
├── README.md                 ← you are here
├── architecture/             System design (built vs planned)
│   ├── 01-system-overview.md
│   ├── 02-voice-paths.md
│   ├── 03-multi-agent.md
│   ├── 04-memory-and-data.md
│   └── 05-deployment-topology.md
├── current-state/            What exists, gaps, roadmap
│   ├── SYSTEM-STATUS.md      Authoritative snapshot
│   ├── WHAT-WE-DID-2026-07-10.md  Sprint changelog
│   ├── DEVELOPMENT-MILESTONES.md  Prioritized milestones
│   ├── what-we-have.md
│   ├── gaps-and-blockers.md
│   └── improvement-roadmap.md
├── operations/               Runbooks and validation
│   ├── ROADMAP-VALIDATION.md  Milestones M1-M9, tiers T0-T3
│   ├── MANUAL-TEST-TRACKER.md Human test matrix
│   ├── local-testing.md
│   └── staging-runbook.md
├── reviews/                  Strategy and external review packs
│   ├── PORTFOLIO-SYSTEM-MOAT.md  Holistic moat and cross-module plan
│   └── EXTERNAL-ENGINEERING-ARCHITECTURE-REVIEW.md
├── insights/                 Research distillations
├── decision-log/             ADRs
├── dev-log/                  Chronological dev notes
└── (legacy guides below)
```

## Quick links

| I want to… | Read |
|------------|------|
| Understand the architecture | [architecture/01-system-overview.md](architecture/01-system-overview.md) |
| See what's built vs missing | [current-state/SYSTEM-STATUS.md](current-state/SYSTEM-STATUS.md) |
| What we shipped this sprint | [current-state/WHAT-WE-DID-2026-07-10.md](current-state/WHAT-WE-DID-2026-07-10.md) |
| Roadmap + validation gates | [operations/ROADMAP-VALIDATION.md](operations/ROADMAP-VALIDATION.md) |
| Portfolio moat and strategy | [reviews/PORTFOLIO-SYSTEM-MOAT.md](reviews/PORTFOLIO-SYSTEM-MOAT.md) |
| Run all 6 agents | `.\scripts\run-six-agents.ps1 -Refresh` |
| Open gaps (prioritized) | [current-state/gaps-and-blockers.md](current-state/gaps-and-blockers.md) |
| Run locally | [operations/local-testing.md](operations/local-testing.md) |
| Deploy VPS | [operations/staging-runbook.md](operations/staging-runbook.md) |
| Configure memory | [MEMORY-STACK.md](MEMORY-STACK.md) |
| Product vision | [CLARITY-FRAMEWORK.md](CLARITY-FRAMEWORK.md) |
| Portfolio integration | [PORTFOLIO-INTEGRATION.md](PORTFOLIO-INTEGRATION.md) |

## Legacy / historical

| Doc | Note |
|-----|------|
| [PLAN-SETUP-REVIEW.md](PLAN-SETUP-REVIEW.md) | 2026-07-07; predates multi-agent — use `current-state/` instead |
| [dev-log/DEV-LOG.md](dev-log/DEV-LOG.md) | Session chronology |
| [VPS-SETUP.md](VPS-SETUP.md) | Aether 8-step checklist |
| [HERMES-COST-OPTIMIZATION.md](HERMES-COST-OPTIMIZATION.md) | Cost directive |
| [SOURCE-MATERIALS.md](SOURCE-MATERIALS.md) | Raw transcript index |