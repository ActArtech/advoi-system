# System overview

ADVoi is a voice-first executive operating layer over an existing portfolio stack (Hermes, FirstMate fleet, Aether). It is **not** a replacement for those systems; it routes attention, surfaces briefs, and speaks results.

> **Doc sync:** Runtime ships **6 agents / 6 frames** and built Aether, Guardian, Squads, and Ingestion verticals. This overview was reconciled with code on branch `fm/advoi-arch-doc-sync-01` (closes arch review gap row *Routing/Decision **Stale***; unblocks M9.4 / GAP-012). Companion: [ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md).

## Design principles

1. **Thin voice layer** — LiveKit + Pipecat handle transport; business logic stays in routing, memory, and decision modules.
2. **Confirmation harness** — High-stakes frames (e.g. deep review) require explicit confirmation before side effects (Guardian).
3. **Ontology-first** (target) — Named frames, agents, and memory write targets; full ontology engine not built yet.
4. **Production-oriented** — Health checks, env-driven config, Docker services, smoke scripts from day one.

## Module map

### Verticals (domain)

| Module | Path | Status |
|--------|------|--------|
| Voice | `advoi/voice/` | **Built** — Pipecat agent, tokens, frame dispatch, memory hooks |
| Decision | `advoi/decision/` | **Built** — Frame catalog (**6 frames**, Options A–F) |
| Memory | `advoi/memory/` | **Built** — Router, Hindsight bridge, Postgres, Redis, review queue |
| Routing | `advoi/routing/` | **Built** — 6 agents, frame runner, daemons, supervisor, run-six |
| API | `advoi/api/` | **Built** — FastAPI HTTP surface |
| LLM | `advoi/llm/` | **Built** — OpenRouter-first credentials |
| Aether | `advoi/aether/` | **Built** — gate, portfolio, architect, lifecycle, service facade |
| Guardian | `advoi/guardian/` | **Built** — confirmation harness, recovery, notifications, auto-restart |
| Squads | `advoi/squads/` | **Built** — registry, dispatch, run-six platform orchestration |
| Fleet | `advoi/fleet/` | **Built** — bridge, trigger, session (when present) |

### Horizontals (cross-cutting)

| Module | Path | Status |
|--------|------|--------|
| Ingestion | `advoi/ingestion/` | **Built** (MVP) — upload, parse, route, store, optional FirstMate dispatch |
| Reporting | `advoi/reporting/` | Stub |
| Ontology | `advoi/ontology/` | Stub |
| Observability | `advoi/observability/` | Partial — system graph; OTel collector in compose (profile `observability`) |

### Web client

| Path | Status |
|------|--------|
| `web/` | **Built** — Next.js 15 PWA; home `/` = onboarding + briefs surface + `VoiceSession` (LiveKit, 6 frames, chips) |
| `web/components/PwaHomeBriefsSurface.tsx` | **Built** — open briefs + review queue cards (`GET /api/briefs`, `GET /api/review-queue`) |
| `web/voice-interface/` | **Built** — Kokoro + Parakeet client loop at `/voice-local` |

## High-level diagram

Six specialist agent daemons (one per decision frame), plus API, voice, and memory bridge:

```mermaid
flowchart TB
  subgraph client [Client]
    PWA[PWA home + VoiceSession]
  end

  subgraph advoi_stack [ADVoi Docker stack]
    API[advoi-api :8010]
    VOICE[advoi-voice Pipecat]
    LK[livekit :7880]
    AG1[advoi-agent-fleet]
    AG2[advoi-agent-briefs]
    AG3[advoi-agent-review]
    AG4[advoi-agent-systems]
    AG5[advoi-agent-memory]
    AG6[advoi-agent-guardian]
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
  AG4 --> RD
  AG5 --> RD
  AG6 --> RD
  VOICE --> BRIDGE
  API --> BRIDGE
  BRIDGE -->|docker exec| HERMES
  AG1 --> FM
  AG4 --> FM
  API --> FM
```

Daemon → agent id mapping (compose `app` profile):

| Compose service | Agent id | Frame id |
|-----------------|----------|----------|
| `advoi-agent-fleet` | `fleet-scout` | `fleet_status` |
| `advoi-agent-briefs` | `brief-curator` | `open_briefs` |
| `advoi-agent-review` | `review-queue` | `queue_deep_review` |
| `advoi-agent-systems` | `systems-pulse` | `systems_pulse` |
| `advoi-agent-memory` | `memory-scout` | `memory_health` |
| `advoi-agent-guardian` | `guardian-sentinel` | `guardian_status` |

Sources: `advoi/routing/agents.py`, `advoi/decision/frames.py`, `docker-compose.yml`. Staging registry: `GET https://advoi-staging.keyteller.com/api/agents` (6 ready).

## Repository layout

```
advoi-system/
├── advoi/                 # Python package
│   ├── api/               # HTTP API
│   ├── aether/            # Portfolio / venture architect
│   ├── decision/          # Frame catalog (6 frames)
│   ├── fleet/             # FirstMate bridge helpers
│   ├── guardian/          # Confirmation + recovery
│   ├── ingestion/         # Upload → route → optional dispatch
│   ├── llm/               # OpenRouter / OpenAI resolution
│   ├── memory/            # Hybrid memory + bridge + review queue
│   ├── routing/           # Agents, frame runner, daemons, run-six
│   ├── squads/            # Crew dispatch + platform orchestration
│   └── voice/             # Pipecat + LiveKit agent
├── web/                   # Next.js PWA
├── deploy/                # Staging compose, livekit.yaml, env templates
├── scripts/               # Deploy, smoke, seed, local test
├── tests/                 # pytest
└── docs/                  # This documentation tree
```

## API surface (implemented)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| POST | `/api/livekit/token` | Mint room JWT for PWA |
| GET | `/api/session` | Frames + agents metadata |
| GET | `/api/frames` | Decision frame list (6) |
| GET | `/api/agents` | Specialist registry + optional Redis `last_run` (6) |
| POST | `/api/frames/{id}/run` | Execute frame via specialist |
| POST | `/api/agents/run-six` | Parallel refresh of all six specialists |
| GET | `/api/diagnostics/voice` | Config checklist (no LiveKit join) |

See [03-multi-agent.md](03-multi-agent.md) for agent/frame table and daemon detail.

## What is explicitly out of scope (today)

- Full free-speech NLU (keyword/intent routing exists; not full semantic NLU)
- Full ontology governance engine (`advoi/ontology/` still stub)
- Multi-tenant SaaS / production multi-user personalization
- Client-side Kokoro/Parakeet loop (designed, not merged)
- Reporting / BI engine on memory events
