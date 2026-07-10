# Postgres migrations

**Ship:** `advoi-data-migrations-01`  
**Code:** `advoi/db/migrations.py` · `deploy/migrations/*.sql` · `tests/test_migrations.py`  
**Boot hook:** `advoi/api/app.py` lifespan → `apply_pending_migrations()`

---

## Apply order

Migrations are **versioned SQL files** under `deploy/migrations/`. Filenames must match:

```text
NNN_description.sql
```

The runner sorts by the leading integer (`NNN`), then by full stem. Current chain:

| Order | File | Creates / changes |
|------:|------|-------------------|
| 0 | `000_baseline_tables.sql` | `memory_events`, `decision_briefs`, `review_queue` |
| 1 | `001_portfolio_events.sql` | `portfolio_events` + indexes + idempotent backfill from `memory_events` |

Tracking table (created by the runner, not a numbered file):

| Table | Purpose |
|-------|---------|
| `schema_migrations` | `(version TEXT PK, checksum TEXT, applied_at TIMESTAMPTZ)` — one row per applied file stem |

**Rules:**

1. Always add new files with a higher `NNN` than the current max (never rewrite applied history on shared DBs).
2. SQL must be **idempotent** (`CREATE … IF NOT EXISTS`, `ON CONFLICT DO NOTHING`) so manual re-runs and partial applies stay safe.
3. `001` depends on `000` for the `memory_events` backfill — do not reorder.
4. Do not put new inline `CREATE TABLE` in Python; add a versioned file instead.

---

## Runtime behaviour

| Condition | Behaviour |
|-----------|-----------|
| `DATABASE_URL` unset | No-op success (`reason=no_database_url`); pending versions listed |
| `DATABASE_URL` set | Connect → ensure `schema_migrations` → apply missing files in order → commit |
| File already in `schema_migrations` | Skipped |
| Connect / execute error | Logged warning; `ok=False` (API still starts — soft-fail matches other PG helpers) |
| Override dir | `ADVOI_MIGRATIONS_DIR=/path/to/sql` |

API image copies `deploy/migrations/` to `/app/deploy/migrations/` (`Dockerfile.api`).

Best-effort ensure paths (when a writer runs without boot):

- `advoi.analytics.pel.ensure_portfolio_events_table` → runner
- `advoi.memory.review_queue.ensure_table` → runner

---

## Local / CI

```bash
# Unit tests (no Postgres required)
uv run pytest tests/test_migrations.py -q

# Optional: apply against a real DSN
export DATABASE_URL=postgresql://advoi:advoi@127.0.0.1:5438/advoi
uv run python -c 'import asyncio; from advoi.db.migrations import apply_pending_migrations; print(asyncio.run(apply_pending_migrations()))'
```

---

## Staging verification (VPS apply parked)

**Status:** Direct SSH apply from this ship is **parked**. Land on `develop`; firstmate / ops promote. After promote + API restart, verify on the staging Postgres (or via a one-shot `advoi-api` container with the same `DATABASE_URL`).

### After promote to www staging

```bash
# 1. Health (API boot should have run migrations)
curl -sf https://advoi-staging.keyteller.com/api/health | jq .

# 2. On VPS when SSH is available — inspect tracking + tables
# (example for compose stack; adjust container name/DSN from deploy/.env)
docker compose --profile app exec -T postgres \
  psql -U advoi -d advoi -c "SELECT version, applied_at FROM schema_migrations ORDER BY version;"

docker compose --profile app exec -T postgres \
  psql -U advoi -d advoi -c "\dt portfolio_events memory_events decision_briefs review_queue schema_migrations"
```

### Expected rows

```text
version                 | applied_at
------------------------+-------------------------------
000_baseline_tables     | <api boot timestamp>
001_portfolio_events    | <api boot timestamp>
```

### Smoke that schema is live

```bash
# Optional: emit a PEL row via frame mock / fleet mock on staging, then:
docker compose --profile app exec -T postgres \
  psql -U advoi -d advoi -c "SELECT COUNT(*) FROM portfolio_events;"
```

### If migrations did not apply

1. Confirm API image includes `/app/deploy/migrations/` (rebuild after this ship).
2. Confirm `DATABASE_URL` in `deploy/.env` points at the staging Postgres service.
3. Check API logs for `migration apply deferred` / `applied N migration(s)`.
4. Re-run apply manually with the same DSN (idempotent).

**Do not** hand-edit `schema_migrations` unless recovering from a broken partial apply with a known checksum mismatch.
