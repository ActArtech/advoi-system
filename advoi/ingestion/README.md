# ingestion/

Large text and document processing engine. Feeds structured knowledge into memory and ontology.

## Purpose

- **Document intake** — PDF, markdown, transcripts, web captures
- **Chunking & extraction** — semantic splits with provenance
- **Embedding pipeline** — prepare vectors for retrieval (future)

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Parse, chunk, normalize text | Voice session handling (→ `voice/`) |
| Source metadata & lineage | Strategic briefs (→ `decision/`) |
| Batch/async processing | Real-time routing (→ `routing/`) |

## Output

Structured chunks with `{ source, timestamp, entity_refs[], content }` → `memory/` operational tier.