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

Set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME` in `.env`.

Enable the collector profile:

```bash
docker compose --profile observability up -d otel-collector
```