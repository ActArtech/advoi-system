# System overview

ADVoi is a voice-first executive operating layer over an existing portfolio stack (Hermes, FirstMate fleet, Aether). It is **not** a replacement for those systems; it routes attention, surfaces briefs, and speaks results.

## Design principles

1. **Thin voice layer** — LiveKit + Pipecat handle transport; business logic stays in routing, memory, and decision modules.
2. **Confirmation harness** — High-stakes frames (e.g. deep review) require explicit confirmation before side effects.
3. **Ontology-first** (target) — Named frames, agents, and memory write targets; full ontology engine not built yet.
4. **Production-oriented** — Health checks, env-driven config, Docker services, smoke scripts from day one.

## Module map

### Verticals (domain)

| Module | Path | Status |
|--------|------|--------|
| Voice | `advoi/voice/` | **Built** — Pipecat agent, tokens, frame dispatch, memory hooks |
| Decision | `advoi/decision/` | **Built** — Frame catalog (3 frames) |
| Memory | `advoi/memory/` | **Built** — Router, Hindsight bridge, Postgres, Redis |
| Routing | `advoi/routing/` | **Built** — Agents, frame runner, daemons, supervisor |
| API | `advoi/api/` | **Built** — FastAPI HTTP surface |
| LLM | `advoi/llm/` | **Built** — OpenRouter-first credentials |
| Aether | `advoi/aether/` | Stub (`__init__.py` only) |
| Guardian | `advoi/guardian/` | Stub |
| Squads | `advoi/squads/` | Stub |

### Horizontals (cross-cutting)

| Module | Path | Status |
|--------|------|--------|
| Ingestion | `advoi/ingestion/` | Stub |
| Reporting | `advoi/reporting/` | Stub |
| Ontology | `advoi/ontology/` | Stub |
| Observability | `advoi/observability/` | Stub; OTel collector in compose (profile `observability`) |

### Web client

| Path | Status |
|------|--------|
| `web/` | **Built** — Next.js 15 PWA, `VoiceSession`, LiveKit client, frame buttons |
| `web/voice-interface/` | **Planned** — Kokoro + Parakeet client loop (not in repo yet) |

## High-level diagram

```mermaid
flowchart TB
  subgraph client [Client]
    PWA[PWA VoiceSession]
  end

  subgraph advoi_stack [ADVoi Docker stack]
    API[advoi-api :8010]
    VOICE[advoi-voice Pipecat]
    LK[livekit :7880]
    AG1[advoi-agent-fleet]
    AG2[advoi-agent-briefs]
    AG3[advoi-agent-review]
    BRIDGE[advoi-memory-bridge :8095]
    PG[(postgres)]
    RD[(redis)]
  end

  subgraph portfolio [Portfolio - read only]
    HERMES[hermes container]
    FM[/opt/firstmate-fleet]
  end

  PWA -->|HTTPS /api| API
  PWA -->|WebRTC| LK
  VOICE --> LK
  API --> PG
  API --> RD
  AG1 --> RD
  AG2 --> RD
  AG3 --> RD
  VOICE --> BRIDGE
  API --> BRIDGE
  BRIDGE -->|docker exec| HERMES
  AG1 --> FM
  API --> FM
```

## Repository layout

```
advoi-system/
├── advoi/                 # Python package
│   ├── api/               # HTTP API
│   ├── decision/          # Frame catalog
│   ├── llm/               # OpenRouter / OpenAI resolution
│   ├── memory/            # Hybrid memory + bridge server
│   ├── routing/           # Agents, frame runner, daemons
│   └── voice/             # Pipecat + LiveKit agent
├── web/                   # Next.js PWA
├── deploy/                # Staging compose, livekit.yaml, env templates
├── scripts/               # Deploy, smoke, seed, local test
├── tests/                 # pytest (8 modules, 37+ tests)
└── docs/                  # This documentation tree
```

## API surface (implemented)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| POST | `/api/livekit/token` | Mint room JWT for PWA |
| GET | `/api/session` | Frames + agents metadata |
| GET | `/api/frames` | Decision frame list |
| GET | `/api/agents` | Specialist registry + optional Redis `last_run` |
| POST | `/api/frames/{id}/run` | Execute frame via specialist |
| GET | `/api/diagnostics/voice` | Config checklist (no LiveKit join) |

## What is explicitly out of scope (today)

- Intent routing / NLU to pick frames from free speech
- Squad execution (FirstMate job triggers from voice)
- Aether venture pipelines
- Guardian automated recovery
- Desktop review brief persistence (review queue is stub)
- Client-side Kokoro/Parakeet loop (designed, not merged)