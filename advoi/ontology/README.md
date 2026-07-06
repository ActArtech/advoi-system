# ontology/

Strategy stack definitions. Single source of truth for entities, relationships, and events.

## Purpose

- **Domain ontology** — ventures, decisions, crews, memory tiers as first-class concepts
- **Named relationships** — explicit semantics between entities (not buried FKs)
- **Event modeling** — time-bound connections via event objects

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Schema definitions, validators | Runtime memory (→ `memory/`) |
| Strategy stack layers | Document parsing (→ `ingestion/`) |
| Governance & versioning | API transport (→ `voice/`) |

## Layers

1. **Upper** — time, identity, lifecycle
2. **Core domain** — venture, decision, crew, session
3. **Vertical** — per-bounded-context extensions

Ontology is a versioned product artifact — not a static diagram.