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

| Doc | Purpose |
|-----|---------|
| [PLAN-SETUP-REVIEW.md](docs/PLAN-SETUP-REVIEW.md) | Stage 1 gaps, blockers, next actions |
| [insights/](docs/insights/README.md) | Distilled insights from conversation `.txt` sources |
| [CLARITY-FRAMEWORK.md](docs/CLARITY-FRAMEWORK.md) | Vision, ontology, evolution, locked decisions |
| [DECISION-LOG.md](docs/decision-log/DECISION-LOG.md) | ADR-style architecture decisions |
| [DEV-LOG.md](docs/dev-log/DEV-LOG.md) | Implementation progress |
| [ERROR-LOG.md](docs/error-log/ERROR-LOG.md) | Guardian failure/recovery log |
| [VERSIONS.md](docs/VERSIONS.md) | Release history |
| [SOURCE-MATERIALS.md](docs/SOURCE-MATERIALS.md) | Conversation source index (main1, main2, etc.) |

## Principles

- **Thin voice layer** — transport only; intelligence lives in verticals/horizontals.
- **Confirmation harness** — consequential actions require explicit verbal confirmation.
- **Ontology-first** — named relationships, events, and bounded contexts drive consistency.
- **Production-oriented** — structured logging, health checks, env-driven config from day one.