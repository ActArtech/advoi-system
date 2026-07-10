# ingestion/

Upload → triage → needs_review → approve → optional FirstMate dev dispatch.

## Lifecycle states (M7.2–M7.3 / moat R4 Pattern C)

Happy path is a strict state machine: **`uploaded` → `triaged` → `needs_review` → `approved` → `dispatched`**. Upload creates an item in `uploaded` only (route metadata may be attached, but status does not advance and there is **no auto-dispatch**). Explicit transitions: `POST …/triage`, `POST …/needs-review`, `POST …/approve`, then `POST …/dispatch-dev`. **Dispatch is rejected unless status is `approved`.** Legacy status `routed` may move to `needs_review` or `approved`; `failed` is terminal. Invalid transitions raise `InvalidTransitionError` (API 409).

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/ingestion/upload` | Multipart file upload (status stays `uploaded`) |
| GET | `/api/ingestion/items` | List inbox queue |
| POST | `/api/ingestion/items/{id}/triage` | `uploaded` → `triaged` |
| POST | `/api/ingestion/items/{id}/needs-review` | `triaged` → `needs_review` |
| POST | `/api/ingestion/items/{id}/approve` | `needs_review` → `approved` |
| POST | `/api/ingestion/items/{id}/dispatch-dev` | Arm fleet + dispatch (requires `approved`) |
| GET | `/api/ingestion/summary` | Queue counts |

## Web UI

`/ingest` — upload form, project hint, dispatch action (dispatch only after approve).

## Flow

```
File → extract_text → route metadata (status=uploaded)
     → triage → needs_review → approve
     → dispatch_item_dev → fm-hermes-trigger work
```

## Env

- `ADVOI_INGESTION_PATH` — default `data/ingestion`
- `ADVOI_INGEST_MAX_BYTES` — default 5MB
- `ADVOI_FLEET_MOCK` — mock FirstMate dispatch in tests

## Supported types (MVP)

`.txt`, `.md`, `.json`, `.csv`, `.log`, `.yaml`
