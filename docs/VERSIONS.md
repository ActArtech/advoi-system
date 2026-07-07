# ADVoi Version History

## v0.1.3 — Hermes cost optimization directive (2026-07-07)

**Status:** Documentation

### Added
- `docs/HERMES-COST-OPTIMIZATION.md` — ADVoi-specific Hermes spend notes
- Canonical `deployment/hermes/HERMES-COST-OPTIMIZATION.md` — full 5-section directive
- Cross-links from `MEMORY-STACK.md`, `PLAN-SETUP-REVIEW.md`, Hermes `README.md`

---

## v0.1.2 — Plan review & insight docs (2026-07-07)

**Status:** Stage 1 code built; deploy blocked

### Added
- `docs/PLAN-SETUP-REVIEW.md` — gaps, blockers, priority actions
- `docs/insights/` — 8 distilled markdown files from conversation `.txt` sources
- Updated `docs/README.md`, `SOURCE-MATERIALS.md`

### Documented blockers
- API port / healthcheck mismatch
- Compose `env_file` path vs `deploy/.env`
- Shelve project not wired; HTTPS 404 on staging

---

## v0.1.1 — VPS clone + infra (2026-07-07)

**Status:** Postgres + Redis on VPS; app profile not healthy

See `dev-log/DEV-LOG.md` entry.

---

## v0.1.0 — Initial Scaffold (2026-07-07)

**Status:** Architecture locked; Stage 1 implementation followed in v0.1.1+

### Added
- Python package scaffold with verticals + horizontals
- `docs/CLARITY-FRAMEWORK.md` — master clarity document
- `docs/decision-log/DECISION-LOG.md` — 25 ADRs
- `docs/dev-log/DEV-LOG.md` — development log
- `docs/error-log/ERROR-LOG.md` — Guardian error log template
- `docs/SOURCE-MATERIALS.md` — conversation source index
- Docker Compose skeleton (PostgreSQL, Redis)
- Web PWA scaffold (`web/`) — LiveKit client in v0.1.1+
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