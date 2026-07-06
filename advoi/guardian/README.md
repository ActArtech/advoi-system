# guardian/

Sentinel layer — security, error detection, and recovery. The confirmation harness lives here.

## Purpose

- **Confirmation harness** — block consequential actions until explicit verbal approval
- **Error detection** — catch drift, hallucinated tool calls, failed integrations
- **Recovery** — graceful degradation, retry policies, session repair

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| AuthZ checks, rate limits | Business logic (→ verticals) |
| Confirmation loops | Model routing (→ `routing/`) |
| Circuit breakers, fallbacks | Logging infrastructure (→ `observability/`) |

## Confirmation Pattern

```
Intent detected → classify risk → low: proceed | high: verbal confirm → proceed | abort
```

Set `ADVOI_CONFIRMATION_REQUIRED=true` in `.env` for production.