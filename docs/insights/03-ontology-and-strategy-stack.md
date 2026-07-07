# Ontology & Strategy Stack

**Source:** `deployment/advoi/ontology.txt`  
**Status:** Specified in CLARITY-FRAMEWORK; `advoi/ontology/` stub

---

## Problem

As systems grow, object identity, relationships, and naming degrade. Architecture, data, and vertical boundaries become harder to maintain without explicit ontology governance.

---

## Layered ontology approach

| Layer | Scope |
|-------|-------|
| Upper ontology | Universal concepts — time, identity, location, lifecycle |
| Core domain ontology | Platform nouns and verbs |
| Vertical ontologies | Per bounded context / business unit |

**Governance:** versioned, enforced artifact — not a static diagram. Embedded in schema validation, API contracts, code generation.

---

## Relationship-based modeling

Between any two entities, **multiple named relationships** are expected (feature, not bug):

```
Customer --places--> Order
Order    --isPlacedBy--> Customer
Customer --owns--> Order
```

Use **reification** when the relationship itself has properties (who approved, when, status).

OWL/SHACL constraints control cardinality — e.g. exactly one `isPlacedBy` per Order.

---

## Event-centric ontology

Don't model everything as static links. Many connections are **events**:

```
OrderPlacementEvent
  ├── Customer participatesIn
  ├── Order isCreatedIn
  ├── hasStatus "Completed"
  └── occurredAt timestamp
```

Benefits: clean history, audit trails, simpler core objects.

---

## Jobs to be done (JTBD)

| Concept | Ontology role |
|---------|---------------|
| Job | Goal user tries to achieve (first-class) |
| Job Instance | Specific attempt |
| triggers | Job Instance → Events |
| satisfies | Event/Solution → Job |
| hasOutcome | Success/failure |

Links JTBD to event model and agentic harness mapping.

---

## Open-source tooling landscape

| Tool | Role |
|------|------|
| Protégé + WebProtégé | Industry-standard editor |
| ROBOT + ODK | Git-based validation, release automation |
| VocBench / Mobi | Team governance |
| Open Ontologies (Rust) | MCP-native, 70+ agent tools |
| Ontosphere | Browser canvas + MCP |
| Semantica | Knowledge graph + decision intelligence |

**Agentic shift:** MCP exposes typed ontology operations — agents plan, call reasoners, iterate with symbolic feedback.

---

## OO development connection

| OO | Ontology |
|----|----------|
| Class | Concept/Class |
| Object | Individual |
| Inheritance | subClassOf |
| Attributes | Data properties |
| Methods | Object properties / rules |

Ontology-first → cleaner OO, DB schemas, API models. Changes in business reality propagate cleanly.

**OO UX:** consistent naming and object relationships → coherent UI patterns across the platform.

---

## ADVoi application

Strategy Stack ontology layers (from CLARITY-FRAMEWORK):

- Named relationships, events, bounded contexts
- Drives consistency between voice, PWA, fleet, and memory
- `advoi/ontology/` holds definitions; not yet populated

**Deferred:** formal Protégé/ROBOT pipeline — start with JSON/event schemas in postgres per project.