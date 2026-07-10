-- PEL: portfolio_events (append-only authority) — moat R1
-- Ship: advoi-analytics-pel-schema-01
-- Requires PG13+ gen_random_uuid() (or pgcrypto / uuid-ossp).

CREATE TABLE IF NOT EXISTS portfolio_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    venture_id      TEXT NOT NULL,
    source          TEXT NOT NULL,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    guardian_status TEXT NULL,
    execution_ref   TEXT NULL,
    trace_id        TEXT NULL,
    legacy_memory_event_id BIGINT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT portfolio_events_legacy_memory_event_id_key
        UNIQUE (legacy_memory_event_id)
);

CREATE INDEX IF NOT EXISTS portfolio_events_venture_ts_idx
    ON portfolio_events (venture_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS portfolio_events_source_type_ts_idx
    ON portfolio_events (source, type, timestamp DESC);

CREATE INDEX IF NOT EXISTS portfolio_events_trace_id_idx
    ON portfolio_events (trace_id)
    WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS portfolio_events_execution_ref_idx
    ON portfolio_events (execution_ref)
    WHERE execution_ref IS NOT NULL;

-- Idempotent backfill from legacy memory_events (safe to re-run).
-- No-op when memory_events is empty or missing.
INSERT INTO portfolio_events (
    timestamp,
    venture_id,
    source,
    type,
    payload,
    guardian_status,
    execution_ref,
    trace_id,
    legacy_memory_event_id,
    created_at
)
SELECT
    COALESCE(me.created_at, NOW()),
    COALESCE(
        me.payload->>'venture_id',
        me.payload->>'project',
        'unknown'
    ),
    'memory',
    me.event_type,
    me.payload,
    me.payload->>'guardian_status',
    COALESCE(
        me.payload->>'execution_ref',
        me.payload->>'job_id',
        me.payload->>'dispatch_id'
    ),
    me.payload->>'trace_id',
    me.id,
    COALESCE(me.created_at, NOW())
FROM memory_events me
ON CONFLICT (legacy_memory_event_id) DO NOTHING;

-- memory_events is NOT dropped here — dual-write / soak window per migration plan.
-- DROP TABLE IF EXISTS memory_events;  -- deferred cutover migration
