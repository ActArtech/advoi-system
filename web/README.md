# ADVoi Web Client (PWA)

Mobile-first web client for voice + decision UI. **No APK** — browser installable PWA.

## Stack

- **Framework:** Next.js 15 (App Router)
- **Styling:** Tailwind CSS 4 + shadcn-style primitives (`components/ui/`)
- **Mobile shell:** Bottom tabs + horizontal snap scroll (inspired by [nextjs-mobile-app-template](https://github.com/tablesawuplink633/nextjs-mobile-app-template))
- **Drawers:** [Vaul](https://github.com/emilkowalski/vaul) (`components/ui/drawer.tsx`)
- **Icons:** lucide-react
- **Voice:** LiveKit Web SDK (Path A); Kokoro/Parakeet client loop (Path B `/voice-local`)
- **State:** Presentation models in pure TS modules; API is source of truth

## Home route (`/`) — mobile shell

Four swipe/tap tabs via `AppShell`:

| Tab | Content |
|-----|---------|
| **Voice** | `PwaHomeOnboarding` + `VoiceSession` (connect, frames, operators) |
| **Agents** | `AgentsOrchestrator` — slice grid, presets, wave/stagger modes, squads, history |
| **Briefs** | `PwaHomeBriefsSurface` (open briefs + review queue) |
| **More** | Links to ingest, dashboard, voice paths + Vaul quick-actions drawer |

Agent slices use `POST /api/agents/orchestrate`, `POST /api/agents/run-six`, `POST /api/frames/{id}/run`, and `POST /api/squads/dispatch`. Pure models in `web/lib/agents/` (Python mirror: `tests/test_agent_slices.py`).

**Agents tab coverage:** 6-slice grid (warm/idle/queued/running/ok/error); run modes parallel | wave x2 | stagger; wave preview; multi-select; presets (morning pulse, ops core, intel, full six); cancel + retry failed; results + session history drawers; squad run/dispatch; run all squads (+ dispatch); 6 + squads via run-six. E2E stub: `web/e2e/agents-orchestrator.spec.ts` (not CI yet).

Legacy CSS modules remain on `VoiceSession` and briefs cards; migrate incrementally to Tailwind/shadcn.

Desktop follow-up: `/briefs/[id]`. Dashboard: `/dashboard`. Server voice: `/voice-server`.

## Features

- [x] LiveKit room connect (mic permission)
- [x] Decision frame buttons (6 frames + operators)
- [x] Open briefs + review queue on home (no `/briefs` navigation required)
- [x] PWA manifest (service worker optional / future)
- [ ] Full offline service worker

## Run

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

Open on mobile Chrome → Add to Home Screen for PWA install. Manual matrix **A11–A17** in `docs/operations/MANUAL-TEST-TRACKER.md`.

## Architecture Rule

**No business logic in web client.** Presentation helpers only (`pwaBriefsSurface.ts`, etc.); intelligence stays on API verticals/horizontals.