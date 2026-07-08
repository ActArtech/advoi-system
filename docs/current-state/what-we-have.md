# What we have

Concrete inventory of the `advoi-system` repo as of 2026-07-08.

## Backend (Python)

### Voice (`advoi/voice/`)

- Pipecat pipeline: OpenAI STT, LLM, TTS via OpenRouter-first credentials
- LiveKit transport (self-hosted dev keys)
- Greeting on first participant
- LiveKit data channel: `speak` and `frame` message types
- Memory recall at session start; retain on turns
- `livekit_env.py` — public vs internal URL resolution
- `respond.py` — warm spoken LLM replies for client voice loop

### API (`advoi/api/app.py`)

- Health, LiveKit token, session metadata
- Frame list and frame execution
- `POST /api/voice/respond` — transcript → warm spoken reply
- Agent registry with Redis-backed `last_run` via `agent_cache`
- Voice and agent diagnostics endpoints

### Routing (`advoi/routing/`)

- Three specialist agents with `speaks_first` lines
- `frame_runner.py` — fleet file snapshot, briefs, review queue
- `agent_daemon.py` — per-agent background ticks
- `agent_supervisor.py` — all three agents in one process (local dev)
- Frame catalog exposes `voice_prompt` per frame (intent hooks; classifier not wired)

### Decision (`advoi/decision/`)

- Three frames: `fleet_status`, `open_briefs`, `queue_deep_review`
- Labels use colon format (`Option A: Fleet status`)
- Shared IDs for PWA buttons and future voice intents

### Copy (`advoi/copy_style.py`)

- `plain_copy()` — strips em/en dashes from user-facing and spoken strings
- Used in `frame_dispatch`, `frame_runner`, and `respond`

### Memory (`advoi/memory/`)

- `MemoryRouter` with tier mapping
- Hindsight bridge HTTP server (`bridge_server.py`)
- Postgres store (briefs)
- Redis store (ephemeral)
- Letta integration scaffold (optional, off by default)
- Guardian log scaffold

### LLM (`advoi/llm/`)

- `resolve_llm_credentials()` — OpenRouter preferred, OpenAI fallback

### Cache (`advoi/cache/`)

- `agent_cache.py` — Redis write/read for agent tick payloads; `last_run` on `/api/agents`

## Frontend (`web/`)

- Next.js 15 App Router, standalone output
- PWA manifest + icons
- `VoiceSession.tsx` — connect, disconnect, 3 frame buttons, LiveKit data channel speak
- `voice-interface/` — `VoiceSTT`, `VoiceTTS`, `VoiceLoop` (Kokoro + Parakeet)
- `/voice-local` — client-side voice loop (no LiveKit)
- COOP/COEP headers in `next.config.ts` for WebGPU / SharedArrayBuffer
- Dev API rewrite to `127.0.0.1:8010`
- `stripEmDash` / warmth helpers in UI and client voice path

**Dependencies:** `kokoro-js`, `parakeet.js`, `onnxruntime-web` in `web/package.json`.

**Not wired:** utterance → frame auto-routing (intent classifier).

## Infrastructure

- `docker-compose.yml` — full stack including 3 agent services
- `deploy/docker-compose.staging.yml` — Traefik labels
- `deploy/livekit.yaml` — dev keys
- Dockerfiles: `Dockerfile.api`, `Dockerfile.voice`, `Dockerfile.web`

## Scripts

| Script | Purpose |
|--------|---------|
| `vps-deploy.sh` | Staging deploy with Shelve guard + env repair |
| `ensure-deploy-secrets.sh` | Merge-fix `.env`, set bridge URL |
| `sync-llm-keys-from-clapart.sh` | Copy LLM keys from clapart |
| `seed-advoi-briefs.sh` | Hindsight + Redis + Postgres briefs |
| `seed-local-briefs.py` | Local Redis/Postgres only |
| `voice-smoke-test.sh` | Public URL journey + voice respond + frame intents |
| `agents-smoke-test.ps1` / `.sh` | Multi-agent frame smoke |
| `run-local-test-stack.ps1` / `.sh` | Docker full stack |
| `run-agents-uv.ps1` / `.sh` | API + supervisor without Docker |
| `bootstrap-local-env.sh` | Create `deploy/.env` from local example |
| `memory-health.sh` | Memory stack check |

## Tests

12 test modules, **69 passing** pytest tests including:

- API health and token
- Frames and frame dispatch
- Fleet snapshot
- Memory write targets
- OpenRouter credential resolution
- LiveKit env
- Voice journey (mock)
- Agent supervisor registry and cache
- `plain_copy` normalization
- `warm_spoken_reply` (voice respond)

```bash
uv run pytest tests/ -q
```

## Documentation (governance)

- `.aether/` — shaped bet, stage, events
- `docs/decision-log/` — ADRs
- `docs/insights/` — distilled research
- `docs/CLARITY-FRAMEWORK.md` — vision
- `docs/architecture/` — **this new tree**
- `docs/current-state/` — gaps and roadmap

## VPS (when healthy)

Per prior sessions (not re-verified in this doc pass):

- Clone at `/opt/advoi`, hosts `advoi.keyteller.com`
- Postgres + Redis on isolated ports
- App stack deployable via `vps-deploy.sh`
- Voice works when `OPENAI_API_KEY` present and `advoi-voice` not crash-looping