# reporting/

Communication layer — stakeholder reports and voice-ready status updates.

## Purpose

- **Status reports** — crew progress, venture health, decision outcomes
- **Stakeholder comms** — formatted outputs for external audiences
- **Voice summaries** — TTS-optimized narratives from operational data

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Report templates, scheduling | Data ingestion (→ `ingestion/`) |
| Voice summary generation | Crew dispatch (→ `squads/`) |
| Delivery channel adapters | Metrics collection (→ `observability/`) |

## Consumers

- `voice/` — reads summaries for TTS playback
- `squads/` — emits progress events consumed here