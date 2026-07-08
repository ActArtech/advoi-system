# ADVoi documentation

**Start here:** [current-state/README.md](current-state/README.md) for honest build status (2026-07-08).

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
│   ├── what-we-have.md
│   ├── gaps-and-blockers.md
│   └── improvement-roadmap.md
├── operations/               Runbooks
│   ├── local-testing.md
│   └── staging-runbook.md
├── insights/                 Research distillations
├── decision-log/             ADRs
├── dev-log/                  Chronological dev notes
└── (legacy guides below)
```

## Quick links

| I want to… | Read |
|------------|------|
| Understand the architecture | [architecture/01-system-overview.md](architecture/01-system-overview.md) |
| See what's built vs missing | [current-state/what-we-have.md](current-state/what-we-have.md) |
| Fix staging voice | [current-state/gaps-and-blockers.md](current-state/gaps-and-blockers.md) |
| Run locally | [operations/local-testing.md](operations/local-testing.md) |
| Deploy VPS | [operations/staging-runbook.md](operations/staging-runbook.md) |
| Configure memory | [MEMORY-STACK.md](MEMORY-STACK.md) |
| Product vision | [CLARITY-FRAMEWORK.md](CLARITY-FRAMEWORK.md) |

## Legacy / historical

| Doc | Note |
|-----|------|
| [PLAN-SETUP-REVIEW.md](PLAN-SETUP-REVIEW.md) | 2026-07-07; predates multi-agent — use `current-state/` instead |
| [dev-log/DEV-LOG.md](dev-log/DEV-LOG.md) | Session chronology |
| [VPS-SETUP.md](VPS-SETUP.md) | Aether 8-step checklist |
| [HERMES-COST-OPTIMIZATION.md](HERMES-COST-OPTIMIZATION.md) | Cost directive |
| [SOURCE-MATERIALS.md](SOURCE-MATERIALS.md) | Raw transcript index |