# Local testing

Two modes: **full Docker** (closest to staging) or **UV-only** (fast mock, no Redis/LiveKit).

## Prerequisites

- Python 3.12+, `uv`
- Node 20+, `npm` (for web)
- Docker Desktop (for full stack only)
- Optional: `OPENAI_API_KEY` for voice path

## Quick start (UV mock — no Docker)

**PowerShell pitfall:** Do not combine `cd ... && $env:VAR="true"` in one line. That is bash syntax and fails in pwsh with `ParserError`. Use `;` or the scripts below.

**Terminal 1 — API + 3 agents (recommended):**

```powershell
cd advoi-system
.\scripts\run-agents-uv.ps1
```

**Or two terminals (foreground, easy to debug):**

```powershell
# Terminal 1
cd advoi-system
.\scripts\start-api.ps1

# Terminal 2
cd advoi-system
.\scripts\start-supervisor.ps1
```

Or bash:

```bash
bash scripts/run-agents-uv.sh
```

Sets `ADVOI_FRAME_MOCK=true`, runs `uv sync`, starts API on `:8010` and `advoi-supervisor` (fleet-scout, brief-curator, review-queue).

If you see `No module named advoi.routing.agent_supervisor`, run `uv sync` from `advoi-system` or use `uv run advoi-supervisor` (not raw `python -m`).

If uvicorn exits with `winerror 10048` / `Address already in use`, port 8010 is already taken. Check `http://127.0.0.1:8010/api/health` — if it returns `ok: true`, the API is already running and you can skip starting it again.

**Terminal 2 — Web:**

```powershell
cd advoi-system
.\scripts\start-web.ps1
```

Or manually:

```powershell
cd web
npm install
npm run dev
```

Open http://localhost:3000

**Smoke test (Windows):**

```powershell
.\scripts\agents-smoke-test.ps1
```

Note: Without Redis, `/api/agents` will not show `last_run`; frame API still works.

---

## Full Docker stack

```powershell
# Start Docker Desktop first
cd advoi-system
.\scripts\run-local-test-stack.ps1
```

Or:

```bash
bash scripts/run-local-test-stack.sh
```

Brings up: postgres, redis, api, 3 agent containers, livekit, voice, web.

Bootstrap env:

```powershell
.\scripts\bootstrap-local-env.ps1
```

Or bash (from `advoi-system` directory only):

```bash
bash scripts/bootstrap-local-env.sh
```

Seed briefs (after postgres/redis up):

```bash
REDIS_URL=redis://127.0.0.1:6382/0 \
DATABASE_URL=postgresql://advoi:advoi@127.0.0.1:5438/advoi \
uv run python scripts/seed-local-briefs.py
```

---

## Test matrix

| Test | Command | Needs |
|------|---------|-------|
| Unit | `uv run pytest tests/ -v` | uv sync |
| Multi-agent | `.\scripts\agents-smoke-test.ps1` | API up |
| Web build | `cd web && npm run build` | node |
| Voice config | `curl http://127.0.0.1:8010/api/diagnostics/voice` | API + keys |

---

## LiveKit voice locally

Requires Docker services `livekit` + `advoi-voice` and LLM key in `deploy/.env`.

1. Set `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `deploy/.env`
2. `docker compose --profile app up -d livekit advoi-voice advoi-api`
3. Open PWA, click **Connect voice**
4. Expect greeting TTS; tap a frame button

If connected but silent: `docker compose logs advoi-voice --tail 50`

---

## Common issues

| Issue | Fix |
|-------|-----|
| WSL bash smoke cannot reach API | Use `agents-smoke-test.ps1` from Windows |
| Redis connection refused in supervisor | Expected without Docker; use full stack or ignore cache warnings |
| Voice crash-loop | Add LLM key to env |
| Frame labels show em dash | Known; see gaps doc |