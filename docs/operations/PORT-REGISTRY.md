# ADVoi port registry

**Purpose:** Single in-repo allocation table for host and container ports, aligned with the VPS shared registry conventions used at `/opt/shared/port-registry.md` (vps-shared).  
**Sources of truth in compose:** root `docker-compose.yml`, `deploy/docker-compose.staging.yml`, `deploy/.env.staging.example`, `deploy/.env.local.example`.  
**Apply on VPS:** `scripts/port-registry-apply.sh` (idempotent append of the advoi row).  
**Related:** [VPS-SETUP.md](../VPS-SETUP.md) · [staging-runbook.md](staging-runbook.md) · [deploy/port-registry-entry.md](../../deploy/port-registry-entry.md)

---

## vps-shared row (copy target)

Canonical columns match `/opt/shared/port-registry.md` and `scripts/port-registry-apply.sh`:

| slug | path | host | ports | notes |
|------|------|------|-------|-------|
| advoi | `/data/projects/advoi` (dev); `/var/www/advoi/{staging,live}`; legacy `/opt/advoi` | advoi-staging.keyteller.com / advoi.keyteller.com | PG 127.0.0.1:5438, Redis 127.0.0.1:6382, API 8010, Voice 8011, Web 3000, mem-bridge 8095, LiveKit 7880/7881, OTEL 4317/4318 | Traefik `advoi-web`, `advoi-api`, `advoi-voice`, `advoi-livekit`; Shelve `ktteam/advoi/staging`; compose project `advoi` |

One-line paste form (legacy path still accepted by apply script):

```text
| advoi | /opt/advoi | advoi.keyteller.com | PG 127.0.0.1:5438, Redis 127.0.0.1:6382, API 8010, Voice 8011, Web 3000 | Traefik advoi-web, advoi-api, advoi-voice; Shelve ktteam/advoi/staging |
```

Verify uniqueness before bind:

```bash
ss -tlnp | grep -E '5438|6382|8010|8011|8095|7880|7881|4317|4318|8888'
```

---

## Host allocation (do not collide)

Host ports are **project-isolated** so ADVoi can coexist with other apps that use default 5432/6379/8000.

| Service | Compose service | Host bind (default) | Env var(s) | Container / internal | Exposure |
|---------|-----------------|---------------------|------------|----------------------|----------|
| PostgreSQL | `postgres` | `127.0.0.1:5438` | `POSTGRES_PORT` | `5432` | localhost only |
| Redis | `redis` | `127.0.0.1:6382` | `REDIS_PORT` | `6379` | localhost only |
| API | `advoi-api` | `8010` (dev/staging host map) | `ADVOI_API_HOST_PORT` / `ADVOI_API_PORT` | `8000` (`ADVOI_API_LISTEN_PORT`) | host map local; staging Traefik `PathPrefix(/api)` |
| Voice | `advoi-voice` | `8011` | `ADVOI_VOICE_PORT` | `8080` | host map local; staging Traefik `PathPrefix(/ws/voice)` |
| Web (PWA) | `advoi-web` | `3000` | `ADVOI_WEB_PORT` | `3000` | host map local; staging Traefik host router |
| Memory bridge | `advoi-memory-bridge` | `127.0.0.1:8095` | `ADVOI_MEMORY_BRIDGE_PORT` | `8095` | localhost only (`HINDSIGHT_BRIDGE_URL`) |
| LiveKit SFU HTTP | `livekit` | `127.0.0.1:7880` | `LIVEKIT_HOST_PORT` | `7880` | localhost / Traefik on staging |
| LiveKit RTC TCP | `livekit` | `7881` | `LIVEKIT_RTC_TCP_PORT` | `7881/tcp` | published (staging keeps RTC ports) |
| LiveKit RTC UDP | `livekit` | `50100–50200/udp` | (fixed range in compose) | same | published for WebRTC |
| OTLP gRPC | `otel-collector` | `4317` | (compose fixed) | `4317` | profile `observability`; `OTEL_EXPORTER_OTLP_ENDPOINT` |
| OTLP HTTP | `otel-collector` | `4318` | (compose fixed) | `4318` | profile `observability` (not used by default ADVoi exporter) |
| OTEL Prometheus | `otel-collector` | `8888` | (compose fixed) | `8888` | profile `observability` |
| Letta (optional) | external overlay | register separately | `LETTA_BASE_URL` | often `8283` | own compose; **must not** reuse advoi host ports |

**Naming notes (vps-shared style):**

- **slug** = `advoi` (`PROJECT_SLUG`) — one row per product, not per container.
- **ports** column summarizes **host** binds operators care about (PG/Redis/API/Voice/Web first).
- Traefik service/router names are `${PROJECT_SLUG}-*` (`advoi-web`, `advoi-api`, `advoi-voice`, `advoi-livekit`).
- Staging compose **resets** published ports for web/api/voice/postgres/redis; only LiveKit RTC stays host-published. Public entry is Traefik on 443.

---

## Env defaults by mode

| Mode | File | API host | Voice host | Web | PG host | Redis host |
|------|------|----------|------------|-----|---------|------------|
| Local Docker | `deploy/.env.local.example` | `8010` | `8011` | `3000` | `5438` | `6382` |
| Staging/legacy VPS | `deploy/.env.staging.example` | `8010` | `8011` | `3000` | `5438` | `6382` |
| Compose bare defaults | `docker-compose.yml` | `8000` if env unset | `8080` if env unset | `3000` | `5438` | `6382` |

Always set `ADVOI_API_HOST_PORT=8010` and `ADVOI_VOICE_PORT=8011` on multi-tenant VPS so host binds match this registry (container listen ports stay 8000 / 8080).

---

## Staging vs local

| Concern | Local | Staging (`deploy/docker-compose.staging.yml`) |
|---------|-------|-----------------------------------------------|
| API / web / voice host ports | Published for curl/browser | `ports: !reset []` — reach via `https://advoi-staging.keyteller.com` |
| Postgres / Redis host ports | Bound to loopback high ports | Not published on host |
| LiveKit RTC | TCP 7881 + UDP range | Same RTC published; SFU HTTP via Traefik |
| OTel | Optional `--profile observability` | Same; env `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317` |

See [staging-runbook.md](staging-runbook.md) for deploy smoke; [VPS-SETUP.md](../VPS-SETUP.md) for three-tier paths.

---

## Sync checklist (M9.1)

- [x] In-repo table (this file) matches compose + env examples
- [x] Copy row documented for `/opt/shared/port-registry.md`
- [x] Apply script: `bash scripts/port-registry-apply.sh` on VPS when `/opt/shared` is writable
- [ ] Optional: mirror the same row into the external `ActArtech/vps-shared` git inventory when that repo is updated (ops outside this tree)
