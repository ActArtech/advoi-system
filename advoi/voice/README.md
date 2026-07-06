# voice/

Thin voice transport layer. Does not own intelligence — routes audio ↔ text to the rest of ADVoi.

## Purpose

- **LiveKit** — real-time WebRTC transport (mobile ↔ VPS agent)
- **Pipecat** — STT → routing → TTS pipeline orchestration
- **Turn management** — VAD, interruptions, speculative acknowledgments

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Session lifecycle, streaming audio | Portfolio decisions (→ `aether/`) |
| STT/TTS plumbing | Crew execution (→ `squads/`) |
| Forwarding transcribed intent | Long-term memory (→ `memory/`) |

## Flow

```
Mobile → LiveKit room → Pipecat pipeline → routing/ → response → TTS → Mobile
```

## Integration

- Consumes `routing/` for intent classification and model selection
- Emits events to `observability/` for latency and session metrics
- Defers consequential actions to `guardian/` confirmation harness