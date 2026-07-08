# Current Stage

**Project:** ADVoi
**Stage:** Build
**Sub-stage:** 1.5 Voice + PWA + Multi-agent
**Entered:** 2026-07-08
**Appetite:** 5 days (staging validation)
**Bet:** Pipecat LiveKit voice, 3 specialist agents, intent routing, client voice loop, staging E2E

## Success signal

User opens PWA at advoi.keyteller.com, connects voice, hears greeting and frame TTS; three background agents cache fleet/briefs/review; voice diagnostics reports `ok: true` with LLM keys present.

## Exit criteria checklist

- [x] Pipecat + LiveKit voice agent with greeting and data-channel frames
- [x] LiveKit STT intent routing to decision frames (`VoiceIntentProcessor`)
- [x] Web PWA with 3 frame buttons, agent freshness chips, `/voice-local` client loop
- [x] API: token, frames, agents, `/api/voice/respond`, `/api/voice/intent`, `/api/review-queue`
- [x] Keyword intent classifier + warmth layer for client voice
- [x] Review queue Postgres persistence (with mock fallback)
- [x] 107 pytest tests; voice-smoke + staging-signoff-precheck pass on staging; CI agents-smoke + staging-smoke jobs
- [x] Traefik live at advoi.keyteller.com with valid deploy/.env and LLM keys (verified 2026-07-08)
- [ ] Human E2E sign-off: mic → STT → TTS on staging (use docs/operations/E2E-SIGNOFF.md)
- [ ] Port registry row synced to shared repo

## Transition history

| Date | From | To | Direction | Decision ref |
|------|------|-----|-----------|--------------|
| 2026-07-07 | Idea | Build 1.1 | forward | ADR-001, ADR-002 |
| 2026-07-08 | Build 1.1 | Build 1.5 | forward | multi-agent, intent, review queue |

## Notes

Infrastructure venture — does not replace gem-dev-shop as active Aether product venture.
P0 for staging: LLM keys in deploy/.env, advoi-voice healthy, Shelve pull disabled.