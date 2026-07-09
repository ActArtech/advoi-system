# aether/

Portfolio manager and venture architect. Routes frames to ventures, reads governance gate, and feeds strategic context into voice and memory.

## Architecture

```
Voice / Frames
     |
     v
AetherService  ---> portfolio.json (ventures, bets, squads)
     |                    |
     +-- gate.py --------> firstmate-fleet/aether-gate-latest.md
     |
     +-- architect.py ---> MemoryRouter (SQUAD_LESSON, VENTURE_BELIEF_UPDATE)
     |
     v
Letta (optional) or operational_store.jsonl
```

## Modules

| Module | Role |
|--------|------|
| `models.py` | Venture, VentureBet, GateSnapshot, PortfolioContext |
| `portfolio.py` | Config-driven venture registry (`data/aether/portfolio.json`) |
| `gate.py` | Parse Aether gate verdict from fleet tree |
| `router.py` | Frame-to-venture enrichment on `detail` |
| `architect.py` | Portfolio context for prompts; post-frame memory retain |
| `service.py` | API facade |
| `lifecycle.py` | Gate-aligned active venture + frame coverage |

## API

| Method | Path |
|--------|------|
| GET | `/api/aether/portfolio` |
| GET | `/api/aether/gate` |
| GET | `/api/aether/routes` |
| GET | `/api/aether/status` |
| GET | `/api/aether/ventures/{id}` |
| POST | `/api/aether/reload` |

## CLI

```bash
uv run advoi aether status
```

## Configuration

```env
AETHER_PORTFOLIO_PATH=data/aether/portfolio.json
FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet
LETTA_ENABLED=false
LETTA_BASE_URL=http://letta:8283
ADVOI_OPERATIONAL_STORE=data/operational-memory.jsonl
```

Staging with Letta: run `scripts/memory-setup-letta.sh`, set `LETTA_ENABLED=true`, redeploy with `scripts/staging-redeploy.sh` (auto-includes `deploy/docker-compose.letta.yml`).

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Venture lifecycle metadata | Voice transport (`voice/`) |
| Frame-to-venture routing | Crew execution (`squads/`) |
| Gate verdict surfacing | Document ingestion (`ingestion/`) |
| Operational memory triggers | Replacing Hermes Hindsight |