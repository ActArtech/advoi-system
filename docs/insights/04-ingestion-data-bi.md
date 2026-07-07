# Ingestion, Warehouse & Business Intelligence

**Source:** `deployment/advoi/data.txt`  
**Status:** Specified; `advoi/ingestion/` stub; postgres running on VPS

---

## Ingestion framework pattern

Modular pipeline layers:

```
Input Adapters → Parser/Extractor → Qualifier/Validator → Enricher → Router
```

- Communicate via well-defined event schemas
- Configure flow in YAML/JSON — not hardcoded
- Business logic stays **outside** the framework

---

## Tool comparison

| Tool | Strength | Weakness |
|------|----------|----------|
| **Unstructured** | Huge messy docs → clean structured chunks | Not full routing engine |
| **Data Prepper** | YAML modular pipelines, multi-destination routing | Weak on giant single blobs |
| **Data-Juicer** | 200+ operators, terabyte scale, LLM data curation | Training/RAG focus, not general ingestion |
| **CocoIndex** | Incremental unstructured → multiple outputs | Evaluate when ingestion starts |

**Recommended combo for ADVoi-scale:** Unstructured (extract) + Data Prepper (route) — or defer until ingestion vertical is active.

---

## Data warehouse on VPS

Warehouse = analytics-optimized store after ingestion.

| Option | Fit for VPS |
|--------|-------------|
| **PostgreSQL** | ✅ Start here — ADVoi already runs PG 5438 |
| DuckDB | File-based analytics, zero server |
| ClickHouse | Large volume, fast queries |
| TimescaleDB / Citus | PG extensions for scale |

---

## BI / decision stack

```
Ingestion → Warehouse (PostgreSQL) → Semantic layer (Cube.js) → BI (Superset/Metabase)
```

| Layer | Role |
|-------|------|
| **Cube.js** | Governed metrics once — single source of truth for KPIs |
| **Superset** | Full visual BI for exploration |
| **Metabase** | Lighter dashboards |

**Decision layer:** everyone works from same Cube definitions — analytics directly influences decisions.

---

## Analytics agents (add to existing agent system)

| Agent | Role |
|-------|------|
| Data Analyst | Warehouse queries, exploration |
| BI Metrics | Cube definitions, consistent KPIs |
| Insight Generator | Analysis → recommendations |
| Visualizer | Chart/dashboard suggestions |

Integrate via supervisor routing — does not disrupt Hermes/fleet workflow agents.

---

## Coolify evaluation

**Rejected** (ADR in CLARITY-FRAMEWORK) — conflicts with agentic deploy model. ADVoi uses Docker Compose + `vps-deploy.sh` per portfolio standard.

---

## ADVoi current state

| Component | Status |
|-----------|--------|
| PostgreSQL | ✅ Running isolated on VPS |
| Redis | ✅ Ephemeral turn storage |
| Ingestion engine | 📋 Stub |
| Cube / Superset | 📋 Deferred |
| Analytics agents | 📋 Deferred |

**Next when activated:** schema-per-project in postgres, Unstructured for large text intake, Cube semantic layer for portfolio KPIs.