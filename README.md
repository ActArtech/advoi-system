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

## Quick Start

```bash
# Copy environment template
cp .env.example .env

# Start infrastructure (Postgres, Redis, placeholders)
docker compose up -d

# Install with uv
uv sync

# Verify package
uv run python -c "import advoi; print(advoi.__version__)"
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