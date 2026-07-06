# squads/

Execution crews. Bridges voice commands to FirstMate and specialized agent crews.

## Purpose

- **FirstMate integration** — Discord/webhook bridge for crew coordination
- **Task dispatch** — translate confirmed voice intents into crew assignments
- **Status relay** — crew progress back to voice via `reporting/`

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Crew dispatch, status polling | Strategic portfolio (→ `aether/`) |
| FirstMate protocol adapter | Voice streaming (→ `voice/`) |
| Work item lifecycle | Decision framing (→ `decision/`) |

## Integration

- Receives confirmed actions from `guardian/`
- Uses `DISCORD_BOT_TOKEN` / `DISCORD_WEBHOOK_URL` from environment
- Publishes completion events to `memory/` (operational tier)