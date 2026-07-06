# ADVoi — Aether Governance Decisions

Synced from venture repo when ADVoi is under proactive Aether governance.  
Architecture ADRs live in `docs/decision-log/DECISION-LOG.md`.

## Active venture

Default: **gem-dev-shop** remains Aether active venture until explicitly switched.

ADVoi is infrastructure for the executive OS — not the active productization target until promoted.

## Memory stack (ADR-026)

| Layer | Store | Scope |
|-------|-------|-------|
| Strategic | Hindsight (Hermes) | Portfolio, governance, synthesis |
| Operational | Letta (v0.2) | Identity, prefs, squad learning |
| Structured | Postgres | Projects, briefs, master-state |
| Ephemeral | Redis | Voice turn window |
| Failures | Guardian log | Not memory |

**Phase 1:** Hindsight only via `hermes memory setup`.

## VPS identity

| Field | Value |
|-------|-------|
| slug | advoi |
| path | /opt/advoi |
| host | advoi.keyteller.com |
| repo | ActArtech/advoi-system |
| Shelve | ktteam/advoi/staging |

## What not to do

- Do not switch active venture to ADVoi without explicit decision
- Do not store fleet backlog as long-term memory
- Do not run Cognee + SurrealDB + Hindsight + Letta simultaneously