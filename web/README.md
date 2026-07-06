# ADVoi Web Client (PWA)

Mobile-first web client for voice + decision UI. **No APK** — browser installable PWA.

## Stack (planned)

- **Framework:** Next.js 15 (App Router)
- **Voice:** LiveKit Web SDK
- **UI:** Decision option cards, project hierarchy, squad status
- **State:** Sync with `master-state.json` via ADVoi API

## Phase 1 Features

- [ ] LiveKit room connect (mic permission)
- [ ] Decision Frame buttons (mirror voice options)
- [ ] Project/session navigation
- [ ] Open Decision Briefs list (desktop-optimized view)
- [ ] PWA manifest + service worker

## Run (once implemented)

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

Open on mobile Chrome → Add to Home Screen for PWA install.

## Architecture Rule

**No business logic in web client.** All intelligence stays on VPS verticals/horizontals.