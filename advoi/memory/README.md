# memory/

Hybrid memory system with three tiers and rolling context protocols.

## Purpose

- **Strategic** — long-horizon facts, preferences, venture context (Postgres)
- **Operational** — session-adjacent state, crew outputs, recent decisions (Redis + Postgres)
- **Ephemeral** — rolling window (last 3–5 turns) + async-compressed summary

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Context window management | Ontology schema (→ `ontology/`) |
| Tier promotion/demotion | Intent routing (→ `routing/`) |
| Summary compression jobs | Full document store (→ `ingestion/`) |

## Context Protocol

```
ephemeral window → overflow → async summarize → operational store → strategic promotion (manual/auto)
```

Backed by `DATABASE_URL` and `REDIS_URL`.