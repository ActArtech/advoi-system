# ingestion/

Upload → parse → route to project → optional FirstMate dev dispatch.

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/ingestion/upload` | Multipart file upload + route |
| GET | `/api/ingestion/items` | List inbox queue |
| POST | `/api/ingestion/items/{id}/dispatch-dev` | Arm fleet + dispatch task to captain |
| GET | `/api/ingestion/summary` | Queue counts |

## Web UI

`/ingest` — upload form, project hint, dispatch toggle.

## Flow

```
File → extract_text → route_document (Aether portfolio + fleet slug)
     → store inbox → optional dispatch_item_dev → fm-hermes-trigger work
```

## Env

- `ADVOI_INGESTION_PATH` — default `data/ingestion`
- `ADVOI_INGEST_MAX_BYTES` — default 5MB
- `ADVOI_FLEET_MOCK` — mock FirstMate dispatch in tests

## Supported types (MVP)

`.txt`, `.md`, `.json`, `.csv`, `.log`, `.yaml`