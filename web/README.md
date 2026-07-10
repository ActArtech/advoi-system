# ADVoi Web Client (PWA)

Mobile-first web client for voice + decision UI. **No APK** — browser installable PWA.

## Stack

- **Framework:** Next.js 15 (App Router)
- **Voice:** LiveKit Web SDK (Path A); Kokoro/Parakeet client loop (Path B `/voice-local`)
- **UI:** Frame/operator controls, home briefs + review queue cards, dashboard
- **State:** Presentation models in pure TS modules; API is source of truth

## Home route (`/`)

Order on the page:

1. **`PwaHomeOnboarding`** — install strip + 60s morning pulse CTA (`systems_pulse`)
2. **`PwaHomeBriefsSurface`** — open briefs (`GET /api/briefs`) + review queue (`GET /api/review-queue`); SWR poll; `advoi:briefs-refresh` after frame runs
3. **`VoiceSession`** — LiveKit connect, 6 frames, operators, chips (state / SLA / Aether gate), confirm parity, error recovery

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