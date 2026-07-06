# ADVoi Version History

## v0.1.0 — Initial Scaffold (2026-07-07)

**Status:** Architecture locked, implementation starting

### Added
- Python package scaffold with verticals + horizontals
- `docs/CLARITY-FRAMEWORK.md` — master clarity document
- `docs/decision-log/DECISION-LOG.md` — 25 ADRs
- `docs/dev-log/DEV-LOG.md` — development log
- `docs/error-log/ERROR-LOG.md` — Guardian error log template
- `docs/SOURCE-MATERIALS.md` — conversation source index
- Docker Compose skeleton (PostgreSQL, Redis)
- Web PWA placeholder (`web/`)
- GitHub repository

### Locked Architecture
- Voice-first executive OS
- LiveKit + Pipecat voice stack
- Aether (portfolio) + Guardian (security) + Squads (execution)
- Horizontal Ingestion + Reporting engines
- Web PWA first (no APK)
- PostgreSQL schema-per-project

### Next (v0.2.0 target)
- Pipecat + LiveKit voice agent on VPS
- Web PWA with LiveKit web client + decision buttons
- Thin wrapper → FirstMate bridge
- PostgreSQL project schemas
- Guardian observability hooks

## Versioning Scheme

| Bump | When |
|------|------|
| **Major** | Breaking architecture change, vertical restructure |
| **Minor** | New vertical/horizontal, new locked decision batch |
| **Patch** | Docs, config, non-breaking implementation |