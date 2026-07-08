# What we have

Concrete inventory of `advoi-system` as of **2026-07-08**, commit `48e7645`.

**Staging verified live:** `https://advoi.keyteller.com` — API 200, 3/3 agents ready, voice diagnostics `ok: true`.

---

## Backend (Python)

### API (`advoi/api/app.py`) — 14 routes, all wired

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health`, `/api/health` | Liveness + agent readiness summary |
| POST | `/api/livekit/token` | Mint LiveKit JWT for PWA join |
| GET | `/api/session` | Room, frames, agents, memory provider |
| GET | `/api/frames` | Decision frame catalog with `voice_prompt` |
| POST | `/api/frames/{id}/run` | Execute frame (optional `confirmed`, `refresh`) |
| GET | `/api/agents` | Agent registry + Redis `last_run` cache |
| POST | `/api/agents/prewarm` | Parallel cache warm for all specialists |
| POST | `/api/voice/intent` | Classify transcript → frame or chat + preview |
| POST | `/api/voice/respond` | Warm spoken reply for client voice loop |
| GET | `/api/review-queue` | Pending deep-review items (Postgres) |
| GET | `/api/review-queue/{id}` | Single review item for desktop brief page |
| GET | `/api/diagnostics/agents` | Agent cache readiness |
| GET | `/api/diagnostics/voice` | Voice journey probe (LLM, LiveKit, memory bridge) |
| GET | `/api/diagnostics/latency` | Health + token + frame timing |

Startup prewarm when `ADVOI_PREWARM_AGENTS=true` (default).

### Voice (`advoi/voice/`)

- **Pipecat pipeline:** transport → STT → memory → **intent processor** → LLM → TTS
- **LiveKit transport** with self-hosted dev keys
- **Greeting** on first participant
- **`VoiceIntentProcessor`** — keyword frame routing, two-turn confirm for review queue
- **Data channel:** `speak` and `frame` message types
- **Memory hooks** — retain voice turns to Redis
- **`respond.py`** — warm spoken replies for Path B
- **`livekit_env.py`** — public vs internal WSS URL resolution

### Routing (`advoi/routing/`)

| Component | Role |
|-----------|------|
| `agents.py` | Registry: fleet-scout, brief-curator, review-queue |
| `frame_runner.py` | Fleet snapshot, open briefs, review queue enqueue |
| `intent.py` | Keyword classifier → frame or chat action |
| `agent_daemon.py` | Per-agent background ticker (Docker services) |
| `agent_supervisor.py` | All three agents in one process (local dev) |
| `agent_bootstrap.py` | Tick + parallel prewarm |
| `agent_config.py` | Frame mapping, interval (45s prod / 15s staging) |

### Decision (`advoi/decision/frames.py`)

| ID | Label | Agent | Confirm |
|----|-------|-------|---------|
| `fleet_status` | Option A: Fleet status | fleet-scout | No |
| `open_briefs` | Option B: Open briefs | brief-curator | No |
| `queue_deep_review` | Option C: Queue deep review | review-queue | Yes |

### Copy (`advoi/copy_style.py`)

`plain_copy()` strips em/en dashes from UI and spoken strings.

### Memory (`advoi/memory/`)

| Module | Role | Status |
|--------|------|--------|
| `router.py` | Tier-aware recall/retain | Wired |
| `hindsight.py` | Strategic memory via HTTP bridge or direct client | Wired, degrades gracefully |
| `bridge_server.py` | Hermes docker.sock bridge (`:8095`) | Wired (separate container) |
| `postgres_store.py` | Briefs + events | Wired (needs `DATABASE_URL`) |
| `review_queue.py` | Deep-review queue + desktop brief URLs | Wired |
| `redis_store.py` | Ephemeral voice turn window | Wired |
| `guardian_log.py` | JSONL error log | Wired |
| `letta.py` | Operational memory | Scaffold (off by default) |

### Cache (`advoi/cache/`)

`agent_cache.py` — Redis write/read for agent ticks; `last_run` on `/api/agents`.

### LLM (`advoi/llm/`)

`resolve_llm_credentials()` — OpenRouter preferred, OpenAI fallback.

---

## Frontend (`web/`)

### Routes

| Route | Component | Path |
|-------|-----------|------|
| `/` | `VoiceSession.tsx` | Path A — LiveKit PWA |
| `/voice-local` | `VoiceLoop.tsx` | Path B — client STT/TTS |
| `/briefs/[id]` | Brief page | Desktop deep-review follow-up from queue URLs |

### VoiceSession features (Path A)

- Connect / disconnect LiveKit room
- Mic publish with echo cancellation
- Remote audio playback (server TTS)
- 3 frame buttons from `/api/frames`
- Confirmation flow for Option C
- Shift+click / double-click refresh for fleet
- Agent freshness chips (30s poll)
- Review queue panel (30s poll)
- Voice intent hints when connected
- `stripEmDash` on all user-facing copy

### voice-interface (Path B)

- `VoiceSTT` — Parakeet (WebGPU/WASM)
- `VoiceTTS` — Kokoro (WebGPU/WASM, speechSynthesis fallback)
- `VoiceLoop` — intent → frame run → respond fallback
- COOP/COEP headers in `next.config.ts` for WebGPU

### PWA

- Manifest + icons 192/512
- Standalone display mode
- No service worker yet (offline = future)

---

## Infrastructure

### Docker Compose (`docker-compose.yml`)

| Profile | Services |
|---------|----------|
| default | postgres, redis |
| `app` | api, web, voice, livekit, memory-bridge, 3 agent daemons |
| `observability` | otel-collector (not wired to app) |

### Staging overlay (`deploy/docker-compose.staging.yml`)

Traefik routes on `advoi.keyteller.com`:

- `/` → web (priority 10)
- `/api/*` → api (priority 50)
- `livekit.advoi.keyteller.com` → livekit SFU

### Dockerfiles

- `Dockerfile.api` — Python API + agents
- `Dockerfile.voice` — Pipecat worker
- `Dockerfile.web` — Next.js standalone (`npm ci`, `.dockerignore`)

---

## Scripts

| Script | Purpose |
|--------|---------|
| `vps-deploy.sh` | Staging deploy; Shelve guard; corrupt env auto-restore |
| `repair-vps-env.sh` | One-shot env repair + recreate edge + agents |
| `ensure-deploy-secrets.sh` | Merge-fix `.env`, staging hosts, interval, keys |
| `sync-llm-keys-from-clapart.sh` | Copy LLM keys from clapart |
| `voice-smoke-test.sh` | Staging journey + diagnostics |
| `agents-smoke-test.ps1` / `.sh` | 3 agents + 3 frames + intent + review queue |
| `run-agents-uv.ps1` / `.sh` | Local API + supervisor without Docker |
| `bootstrap-local-env.ps1` / `.sh` | Create local `deploy/.env` |
| `memory-health.sh` | Memory stack probe |

---

## Tests — 107 passing (15 modules)

```bash
uv run pytest tests/ -q
# 105 passed
```

| Module | Focus |
|--------|-------|
| `test_api.py` | Health, token |
| `test_voice_journey.py` | Full API journey, diagnostics |
| `test_intent.py` | Classifier, intent processor, voice respond routing |
| `test_frames.py` | Frame catalog, dispatch |
| `test_review_queue.py` | Postgres queue, API, frame integration |
| `test_memory_bridge_diagnostics.py` | Bridge probe, voice diagnostics |
| `test_fleet_snapshot.py` | Fleet disk parsing |
| `test_agent_cache.py` | Redis cache behavior |
| `test_agent_supervisor.py` | All specialists covered |
| `test_openrouter.py` | Credential resolution |
| `test_livekit_env.py` | URL + dev keys |
| `test_copy_style.py` | Em-dash stripping |
| `test_memory.py` | Write targets, router |
| `test_voice_respond.py` | Respond endpoint |
| `test_agent_bootstrap.py` | Tick + prewarm |

---

## CI (`.github/workflows/advoi-ci.yml`)

| Job | What it runs |
|-----|--------------|
| `python` | Full pytest |
| `web` | `npm ci` + production build |
| `agents-smoke` | API up + intent/review tests + curl smoke |

---

## VPS staging (verified 2026-07-08)

| Item | Value |
|------|-------|
| Host | `deploy@187.77.140.216` |
| Path | `/opt/advoi` |
| Storefront | `https://advoi.keyteller.com` |
| LiveKit | `wss://livekit.advoi.keyteller.com` |
| Agent interval | 15s (`ADVOI_AGENT_INTERVAL_SECS`) |
| Containers | api, web, voice, livekit, 3 agents, postgres, redis, memory-bridge — all Up |
| GitHub | `ActArtech/advoi-system` @ `48e7645` |

---

## Scaffold only (not production-ready)

| Item | Notes |
|------|-------|
| Letta operational memory | Code present, `LETTA_ENABLED=false` |
| Guardian auto-recovery | Log scaffold only |
| Aether / Squads | Package stubs |
| React Flow dashboard | Not started |
| PWA service worker | Manifest only |
| Path B iOS WebGPU | Not device-tested |
| OTel app traces | Collector profile exists, not wired |
| Traefik `/ws/voice` route | Legacy label; Stage 1 uses LiveKit not WS |

---

## Documentation

| Path | Purpose |
|------|---------|
| `docs/current-state/` | This folder — honest status |
| `docs/architecture/` | System design |
| `docs/operations/` | Runbooks, E2E sign-off |
| `.aether/STAGE.md` | Build 1.5 governance |