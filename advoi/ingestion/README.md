# ingestion/

Upload → triage → needs_review → approve → optional FirstMate dev dispatch.

## Lifecycle states (M7.2–M7.3 / moat R4 Pattern C)

Happy path is a strict state machine: **`uploaded` → `triaged` → `needs_review` → `approved` → `dispatched`**. Upload creates an item in `uploaded` only (route metadata may be attached, but status does not advance and there is **no auto-dispatch**). Explicit transitions: `POST …/triage`, `POST …/needs-review`, `POST …/approve`, then `POST …/dispatch-dev`. **Dispatch is rejected unless status is `approved`.** Legacy status `routed` may move to `needs_review` or `approved`; `failed` is terminal. Invalid transitions raise `InvalidTransitionError` (API 409).

## Keyword triage classifier (M7.2)

Module: [`triage.py`](triage.py) — heuristic scorer over **route metadata + content preview** (not LLM / not full Phase 2 UI).

| Target | When |
|--------|------|
| `triaged` | Clear project slug, usable route confidence, no urgent/review/ambiguity flags |
| `needs_review` | Missing project, low route confidence (`< 0.4`), thin content, high/urgent priority, review or ambiguity keywords |

`POST …/triage` and `triage_item()` always re-route when the blob is present, store the decision on `item.extra["triage"]` (`target_status`, `score`, `reasons`, `labels`, `signals`), step to `triaged`, then auto-advance to `needs_review` when the classifier says so (state machine forbids a direct `uploaded → needs_review` jump).

**Optional auto-triage on upload** — form/flag `auto_triage` (default **false**). When true, upload runs the same classifier path after route metadata is attached. Safer default keeps upload as pure intake.

Out of scope here: batch upload UI, voice triage inbox (deferred L).

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/ingestion/upload` | Multipart file upload (status stays `uploaded`; optional `auto_triage=true`) |
| GET | `/api/ingestion/items` | List inbox queue |
| POST | `/api/ingestion/items/{id}/triage` | Classifier + `uploaded` → `triaged` (or `needs_review`) |
| POST | `/api/ingestion/items/{id}/needs-review` | `triaged` → `needs_review` |
| POST | `/api/ingestion/items/{id}/approve` | `needs_review` → `approved` |
| POST | `/api/ingestion/items/{id}/dispatch-dev` | Arm fleet + dispatch (requires `approved`) |
| GET | `/api/ingestion/summary` | Queue counts |

## Web UI

`/ingest` — upload form (project + optional venture hint), queue with per-item lifecycle
actions: **Triage → Needs review → Approve → Dispatch to FirstMate**. No auto-dispatch
checkbox; dispatch only when status is `approved`. Failed / ontology 422 errors surface
in the status banner and on the item card. Helpers: `web/components/ingestLifecycle.ts`;
tests: `tests/test_ingest_ui_lifecycle.py`, stub `web/e2e/ingest-lifecycle.spec.ts`.

## Flow

```
File → extract_text → route metadata (status=uploaded)
     → triage classifier (triage.py) → triaged | needs_review
     → approve → dispatch_item_dev → fm-hermes-trigger work
```

## Env

- `ADVOI_INGESTION_PATH` — default `data/ingestion`
- `ADVOI_INGEST_MAX_BYTES` — default 5MB
- `ADVOI_FLEET_MOCK` — mock FirstMate dispatch in tests

## Supported types (MVP)

`.txt`, `.md`, `.json`, `.csv`, `.log`, `.yaml`

## Tests

- `tests/test_ingestion_triage.py` — classifier output + transitions to `triaged` / `needs_review`
- `tests/test_ingestion_lifecycle.py` — full state machine
- `tests/test_ingestion.py` — upload, route, dispatch
