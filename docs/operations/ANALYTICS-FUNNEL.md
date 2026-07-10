# Analytics funnel — PWA connect → success (PEL)

**Purpose:** Query the Path A PWA conversion funnel from append-only Postgres `portfolio_events` (Portfolio Event Log).  
**Ships:** `advoi-analytics-pel-schema-01`, `advoi-analytics-pwa-beacon-01`, confirm parity (`advoi-pwa-confirm-parity-01`).  
**Schema:** [architecture/07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md) · migration `deploy/migrations/001_portfolio_events.sql`  
**Wire:** `POST /api/events` ← `web/components/pwaBeacon.ts` ← `VoiceSession` UI state machine

---

## 1. Funnel overview

Happy path (client beacons only):

```
pwa_connect → frame_tap → confirm_shown → confirm_accept
     │              │            │               │
   CONNECT_OK   FRAME_START  CONFIRMATION_    confirm tap /
                             REQUIRED         voice confirm
```

| Stage | PEL `type` | When emitted | Default `guardian_status` | UI / API trigger |
|-------|------------|--------------|---------------------------|------------------|
| Connect | `pwa_connect` | LiveKit connect succeeds | (null) | `CONNECT_OK` |
| Frame | `frame_tap` | Operator starts a frame/action | (null) | `FRAME_START` |
| Confirm shown | `confirm_shown` | Guardian requires confirmation | `pending` | `CONFIRMATION_REQUIRED` |
| Success | `confirm_accept` | User accepts confirmation | `allowed` | Confirm button / voice accept |
| Error | `error` | Connect or session failure | (null) | `CONNECT_FAIL`, `ERROR` |

**Common row shape for PWA beacons**

| Column | Value |
|--------|--------|
| `source` | `api` |
| `venture_id` | usually `advoi` (client default) |
| `payload.client` | `pwa` |
| `payload.session_id` | browser session id (also top-level request field) |
| `payload.ui_event` | e.g. `CONNECT_OK`, `FRAME_START` (when mapped from reducer) |

**Not in this funnel (server-side PEL, separate analytics)**

| `type` | `source` | Notes |
|--------|----------|--------|
| `frame_run` | `api` / `daemon` | Server choke point after `run_frame` |
| `voice_intent` | `voice` | Operator/frame intent only |
| `fleet_trigger` / `guardian_gate` | `fleet` | Bridge invoke + gate evaluation |

Client beacons intentionally reject `frame_run` (422). Use server rows for backend completion rates; use this funnel for UI conversion.

---

## 2. Prerequisites

```bash
# Staging / VPS Postgres (DATABASE_URL on API host)
psql "$DATABASE_URL" -c '\d portfolio_events'
```

Indexes useful for funnel queries:

- `(source, type, timestamp DESC)` — stage counts over time
- `(venture_id, timestamp DESC)` — venture slice
- `payload->>'session_id'` — session-level conversion (JSON path; no dedicated index yet)

Optional filter for PWA-only traffic:

```sql
AND source = 'api'
AND payload->>'client' = 'pwa'
```

---

## 3. Stage queries

Replace the time window as needed. Default window below: last 7 days.

### 3.1 `pwa_connect` — entry (connect success)

```sql
-- Distinct sessions that connected
SELECT
  COUNT(*) AS connect_events,
  COUNT(DISTINCT payload->>'session_id') AS sessions
FROM portfolio_events
WHERE type = 'pwa_connect'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

```sql
-- Connects per day
SELECT
  date_trunc('day', timestamp) AS day,
  COUNT(*) AS connects,
  COUNT(DISTINCT payload->>'session_id') AS sessions
FROM portfolio_events
WHERE type = 'pwa_connect'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1;
```

### 3.2 `frame_tap` — frame / action start

```sql
SELECT
  COUNT(*) AS frame_taps,
  COUNT(DISTINCT payload->>'session_id') AS sessions,
  COUNT(DISTINCT COALESCE(payload->>'frame_id', payload->>'intent_id')) AS distinct_frames
FROM portfolio_events
WHERE type = 'frame_tap'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

```sql
-- Top frames tapped
SELECT
  COALESCE(payload->>'frame_id', payload->>'intent_id', '(unknown)') AS frame,
  COUNT(*) AS taps
FROM portfolio_events
WHERE type = 'frame_tap'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY taps DESC
LIMIT 20;
```

### 3.3 `confirm_shown` — guardian confirmation UI

```sql
SELECT
  COUNT(*) AS confirm_shown,
  COUNT(DISTINCT payload->>'session_id') AS sessions,
  COUNT(*) FILTER (WHERE guardian_status = 'pending') AS pending_status
FROM portfolio_events
WHERE type = 'confirm_shown'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

### 3.4 `confirm_accept` — success (user accepted)

```sql
SELECT
  COUNT(*) AS confirm_accepts,
  COUNT(DISTINCT payload->>'session_id') AS sessions,
  COUNT(*) FILTER (WHERE guardian_status = 'allowed') AS allowed_status
FROM portfolio_events
WHERE type = 'confirm_accept'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days';
```

### 3.5 `error` — drop-offs and failures

```sql
SELECT
  COUNT(*) AS errors,
  COUNT(DISTINCT payload->>'session_id') AS sessions,
  COALESCE(payload->>'ui_event', payload->>'kind', '(unspecified)') AS kind,
  COUNT(*) AS n
FROM portfolio_events
WHERE type = 'error'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY 3
ORDER BY n DESC;
```

```sql
-- Recent error payloads (ops triage)
SELECT
  timestamp,
  payload->>'session_id' AS session_id,
  payload->>'ui_event' AS ui_event,
  payload
FROM portfolio_events
WHERE type = 'error'
  AND source = 'api'
  AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 50;
```

---

## 4. Funnel conversion (session-level)

Count **sessions** that reached each stage at least once. Sessions without `session_id` are excluded from conversion ratios.

```sql
WITH window AS (
  SELECT *
  FROM portfolio_events
  WHERE source = 'api'
    AND payload->>'client' = 'pwa'
    AND timestamp >= NOW() - INTERVAL '7 days'
    AND type IN (
      'pwa_connect',
      'frame_tap',
      'confirm_shown',
      'confirm_accept',
      'error'
    )
),
per_session AS (
  SELECT
    payload->>'session_id' AS session_id,
    BOOL_OR(type = 'pwa_connect') AS reached_connect,
    BOOL_OR(type = 'frame_tap') AS reached_frame,
    BOOL_OR(type = 'confirm_shown') AS reached_confirm_shown,
    BOOL_OR(type = 'confirm_accept') AS reached_success,
    BOOL_OR(type = 'error') AS had_error
  FROM window
  WHERE payload->>'session_id' IS NOT NULL
    AND payload->>'session_id' <> ''
  GROUP BY 1
)
SELECT
  COUNT(*) FILTER (WHERE reached_connect) AS s_connect,
  COUNT(*) FILTER (WHERE reached_frame) AS s_frame,
  COUNT(*) FILTER (WHERE reached_confirm_shown) AS s_confirm_shown,
  COUNT(*) FILTER (WHERE reached_success) AS s_success,
  COUNT(*) FILTER (WHERE had_error) AS s_error,
  -- Step rates (null-safe when denominator is 0)
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE reached_frame)
    / NULLIF(COUNT(*) FILTER (WHERE reached_connect), 0),
    1
  ) AS pct_connect_to_frame,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE reached_confirm_shown)
    / NULLIF(COUNT(*) FILTER (WHERE reached_frame), 0),
    1
  ) AS pct_frame_to_confirm,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE reached_success)
    / NULLIF(COUNT(*) FILTER (WHERE reached_confirm_shown), 0),
    1
  ) AS pct_confirm_to_accept,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE reached_success)
    / NULLIF(COUNT(*) FILTER (WHERE reached_connect), 0),
    1
  ) AS pct_connect_to_success
FROM per_session;
```

### 4.1 Ordered stage counts (event volume, not unique sessions)

```sql
SELECT
  type,
  COUNT(*) AS events
FROM portfolio_events
WHERE source = 'api'
  AND type IN (
    'pwa_connect',
    'frame_tap',
    'confirm_shown',
    'confirm_accept',
    'error'
  )
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY type
ORDER BY
  CASE type
    WHEN 'pwa_connect' THEN 1
    WHEN 'frame_tap' THEN 2
    WHEN 'confirm_shown' THEN 3
    WHEN 'confirm_accept' THEN 4
    WHEN 'error' THEN 5
  END;
```

### 4.2 Drop-off: connected but never tapped a frame

```sql
WITH connects AS (
  SELECT DISTINCT payload->>'session_id' AS session_id
  FROM portfolio_events
  WHERE type = 'pwa_connect'
    AND source = 'api'
    AND timestamp >= NOW() - INTERVAL '7 days'
    AND payload->>'session_id' IS NOT NULL
),
frames AS (
  SELECT DISTINCT payload->>'session_id' AS session_id
  FROM portfolio_events
  WHERE type = 'frame_tap'
    AND source = 'api'
    AND timestamp >= NOW() - INTERVAL '7 days'
    AND payload->>'session_id' IS NOT NULL
)
SELECT c.session_id
FROM connects c
LEFT JOIN frames f USING (session_id)
WHERE f.session_id IS NULL
LIMIT 100;
```

### 4.3 Confirm shown without accept (abandonment)

```sql
WITH shown AS (
  SELECT DISTINCT payload->>'session_id' AS session_id
  FROM portfolio_events
  WHERE type = 'confirm_shown'
    AND source = 'api'
    AND timestamp >= NOW() - INTERVAL '7 days'
    AND payload->>'session_id' IS NOT NULL
),
accepted AS (
  SELECT DISTINCT payload->>'session_id' AS session_id
  FROM portfolio_events
  WHERE type = 'confirm_accept'
    AND source = 'api'
    AND timestamp >= NOW() - INTERVAL '7 days'
    AND payload->>'session_id' IS NOT NULL
)
SELECT s.session_id
FROM shown s
LEFT JOIN accepted a USING (session_id)
WHERE a.session_id IS NULL
LIMIT 100;
```

---

## 5. Session timeline (debug one user journey)

```sql
SELECT
  timestamp,
  type,
  guardian_status,
  execution_ref,
  payload->>'ui_event' AS ui_event,
  payload->>'frame_id' AS frame_id,
  payload
FROM portfolio_events
WHERE payload->>'session_id' = :'session_id'  -- psql variable, or hardcode
  AND source = 'api'
ORDER BY timestamp ASC;
```

---

## 6. Join client funnel to server completion (optional)

When a confirm leads to fleet/frame work, correlate by time window + `execution_ref` / frame id:

```sql
-- Server frame_run after a PWA frame_tap (same day, same frame_id hint)
SELECT
  c.timestamp AS tap_at,
  c.payload->>'session_id' AS session_id,
  c.payload->>'frame_id' AS frame_id,
  s.timestamp AS frame_run_at,
  s.type AS server_type,
  s.payload->>'status' AS status
FROM portfolio_events c
LEFT JOIN LATERAL (
  SELECT *
  FROM portfolio_events s
  WHERE s.type IN ('frame_run', 'fleet_trigger', 'guardian_gate')
    AND s.timestamp BETWEEN c.timestamp AND c.timestamp + INTERVAL '5 minutes'
    AND (
      s.payload->>'frame_id' = c.payload->>'frame_id'
      OR s.execution_ref = c.execution_ref
    )
  ORDER BY s.timestamp
  LIMIT 1
) s ON TRUE
WHERE c.type = 'frame_tap'
  AND c.source = 'api'
  AND c.timestamp >= NOW() - INTERVAL '7 days'
ORDER BY c.timestamp DESC
LIMIT 50;
```

---

## 7. Curl smoke (T0 / staging without SQL)

```bash
# Insert a connect beacon (API must have DATABASE_URL or ADVOI_PEL_MEMORY)
curl -sS -X POST "${API_BASE}/api/events" \
  -H 'Content-Type: application/json' \
  -d '{"type":"pwa_connect","venture_id":"advoi","session_id":"smoke-1","payload":{"ui_event":"CONNECT_OK"}}'

# Allowed types only — unknown types → 422
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "${API_BASE}/api/events" \
  -H 'Content-Type: application/json' \
  -d '{"type":"page_view"}'
```

T0 automated: `tests/test_pwa_beacon_events.py` (with `ADVOI_PEL_MEMORY=true`).

---

## 8. Interpretation notes

| Observation | Likely meaning |
|-------------|----------------|
| High connect, low frame_tap | Users land but do not start an action (UX / discoverability) |
| High frame_tap, low confirm_shown | Most frames do not require Guardian confirm (expected for low-risk) |
| High confirm_shown, low confirm_accept | Confirmation copy friction or abandon (confirm parity ship targets this) |
| High error with `CONNECT_FAIL` | LiveKit / network / token issues |
| `confirm_accept` without prior `confirm_shown` same session | Race, multi-tab, or partial beacon loss — investigate timeline |

**Success definition for this funnel:** session emitted `confirm_accept` after a guardian-gated path. Frames that never require confirmation convert on `frame_tap` (and optionally server `frame_run`) without reaching confirm stages — report both gated conversion and overall frame engagement.

---

## 9. Related

| Resource | Path |
|----------|------|
| PEL schema + emit points | [docs/architecture/07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md) |
| Migration SQL | `deploy/migrations/001_portfolio_events.sql` |
| Write path | `advoi/analytics/pel.py` (`append_event`, `PWA_BEACON_EVENT_TYPES`) |
| HTTP | `POST /api/events` in `advoi/api/app.py` |
| Client beacon | `web/components/pwaBeacon.ts` |
| UI state machine | `web/components/voiceSessionState.ts` |
| Confirm parity | `web/components/confirmParity.ts` |
| Roadmap | [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) (M10 analytics / PEL) |
| Agent notes | `AGENTS.md` § PWA thin beacon → PEL |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Initial funnel doc + SQL (`advoi-analytics-funnel-doc-01`) |
