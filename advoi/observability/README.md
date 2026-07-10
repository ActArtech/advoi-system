# observability/

Cross-cutting telemetry — structured logs, metrics, distributed tracing.

## Purpose

- **Structured logging** — `structlog` with correlation IDs
- **Metrics** — session latency, routing decisions, confirmation rates
- **Tracing** — OTLP export to SigNoz via collector

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Log/metric/trace instrumentation | Business error recovery (→ `guardian/`) |
| OTLP exporter config | SigNoz server deployment |
| Health check helpers | Alert routing policies |

## Configuration

| Env | Staging default | Notes |
|-----|-----------------|-------|
| `OTEL_ENABLED` | `true` in `deploy/.env.staging.example` | Master switch |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | **gRPC** OTLP (port 4317, not HTTP 4318) |
| `OTEL_SERVICE_NAME` | `advoi` | Resource attribute |

Local / disabled:

```bash
# .env
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=advoi
```

Enable the collector profile:

```bash
docker compose --profile observability up -d otel-collector
```

Staging redeploy starts the collector automatically when `OTEL_ENABLED=true`:

```bash
bash scripts/staging-redeploy.sh
```

### Diagnostics (moat R6)

`GET /api/diagnostics/platform` returns:

- `otel.enabled` / `otel.packages_installed` / `otel.instrumented`
- `otel.collector_reachable` — TCP probe to OTLP endpoint
- `otel.otel_ready` / top-level `otel_ready` — enabled + packages + collector reachable

### Guardian JSONL correlation

When `OTEL_ENABLED=true`, each Guardian JSONL record includes top-level `trace_id`
(hex string or `null` if no active span). See `advoi/memory/guardian_log.py`.

**VPS note:** Staging promote may be SSH-parked; land wiring on `develop` first, then
set `OTEL_ENABLED=true` on the VPS `deploy/.env` and redeploy when host access is available.