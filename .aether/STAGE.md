# Current Stage

**Project:** ADVoi
**Stage:** Build
**Sub-stage:** 1.1 Voice + PWA
**Entered:** 2026-07-07
**Appetite:** 3 days
**Bet:** Stage 1 Pipecat agent + web client + port registry + Aether bootstrap

## Success signal

User opens PWA, connects mic, hears ADVoi in LiveKit room; API health and token routes respond; port registry row present on VPS.

## Exit criteria checklist

- [x] Pipecat + LiveKit voice agent code path
- [x] Web PWA scaffold with LiveKit client
- [x] API token endpoint
- [ ] Traefik route live at advoi.keyteller.com (DNS + deploy)
- [x] `.aether/` bootstrap complete on repo
- [ ] Port registry row on VPS `/opt/shared/port-registry.md`

## Transition history

| Date | From | To | Direction | Decision ref |
|------|------|-----|-----------|--------------|
| 2026-07-07 | Idea | Build | forward | ADR-001, ADR-002 |

## Notes

Infrastructure venture — does not replace gem-dev-shop as active Aether product venture.