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

Full: `docs/decision-log/DECISION-LOG.md` → **ADR-026**.

## Portfolio Event Log (ADR-027)

**`portfolio_events` is the single control-plane event authority.** Typed append-only PEL (venture, source, type, guardian, execution, trace). Dual-run with `memory_events` until soak; no live Hindsight double-write (ADR-026 boundary).

Full: `docs/decision-log/DECISION-LOG.md` → **ADR-027**.

## Guardian write-path hard-gate (ADR-028)

**All live `invoke_fleet_trigger` / fm-bridge paths require Guardian post-gate tokens** when confirmation policy is on. Convention is insufficient — structural enforce at low-level invoke; public entry via `fleet_trigger_from_voice`. No bare free-form API invoke.

Full: `docs/decision-log/DECISION-LOG.md` → **ADR-028**. Related: ADR-006 · `docs/architecture/06-vertical-boundaries.md`.

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
- Do not invoke fm-bridge / fleet live shell without Guardian post-gate tokens (ADR-028)
- Do not treat `memory_events` as long-term control-plane authority (ADR-027)
