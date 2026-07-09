# ADVoi

Voice-first personal AI operating system.

## Architecture

ADVoi is organized as **verticals** (domain capabilities) and **horizontals** (cross-cutting services).

### Verticals

| Module | Role |
|--------|------|
| `voice/` | LiveKit transport + Pipecat pipeline (thin wrapper) |
| `aether/` | Portfolio manager + venture architect |
| `guardian/` | Security, error detection, recovery (Sentinel) |
| `squads/` | Execution crews (FirstMate integration) |
| `decision/` | Decision frames, briefs, optionality |
| `memory/` | Hybrid memory (strategic / operational / ephemeral) |

### Horizontals

| Module | Role |
|--------|------|
| `ingestion/` | Large text/document processing engine |
| `reporting/` | Communication & stakeholder reports |
| `routing/` | Intent classification, model routing, token management |
| `ontology/` | Strategy stack definitions |
| `observability/` | Logs, metrics, SigNoz integration |

## VPS deploy (Aether standard)

See **[docs/VPS-SETUP.md](docs/VPS-SETUP.md)** — 8-step checklist for `/opt/advoi` @ `advoi.keyteller.com`.

Memory: **[docs/MEMORY-STACK.md](docs/MEMORY-STACK.md)** — start Hindsight via Hermes; Letta optional v0.2.

Hermes spend: **[docs/HERMES-COST-OPTIMIZATION.md](docs/HERMES-COST-OPTIMIZATION.md)** — cost directive before scaling voice/memory.

## Quick Start (local)

```bash
cp deploy/.env.staging.example deploy/.env
docker compose up -d
uv sync
uv run python -c "from advoi.memory import MemoryRouter; print('memory OK')"
```

## Layout

```
advoi-system/
├── advoi/              # Python package
│   ├── voice/          # Vertical
│   ├── aether/
│   ├── guardian/
│   ├── squads/
│   ├── decision/
│   ├── memory/
│   ├── ingestion/      # Horizontal
│   ├── reporting/
│   ├── routing/
│   ├── ontology/
│   └── observability/
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Documentation

**Hub:** [docs/README.md](docs/README.md)

| Section | Purpose |
|---------|---------|
| [docs/architecture/](docs/architecture/README.md) | System design, voice paths, multi-agent, deployment |
| [docs/current-state/SYSTEM-STATUS.md](docs/current-state/SYSTEM-STATUS.md) | **Authoritative** what we have + gaps |
| [docs/current-state/WHAT-WE-DID-2026-07-10.md](docs/current-state/WHAT-WE-DID-2026-07-10.md) | Multi-agent sprint changelog |
| [docs/current-state/DEVELOPMENT-MILESTONES.md](docs/current-state/DEVELOPMENT-MILESTONES.md) | Prioritized milestones |
| [docs/current-state/](docs/current-state/README.md) | Inventory, roadmap, manual test tracker |
| [docs/operations/](docs/operations/README.md) | Local testing and staging runbook |
| [docs/insights/](docs/insights/README.md) | Research distillations |
| [docs/decision-log/](docs/decision-log/DECISION-LOG.md) | ADRs |
| [docs/CLARITY-FRAMEWORK.md](docs/CLARITY-FRAMEWORK.md) | Product vision |

## Principles

- **Thin voice layer** — transport only; intelligence lives in verticals/horizontals.
- **Confirmation harness** — consequential actions require explicit verbal confirmation.
- **Ontology-first** — named relationships, events, and bounded contexts drive consistency.
- **Production-oriented** — structured logging, health checks, env-driven config from day one.