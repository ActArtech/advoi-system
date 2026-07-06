# Portfolio Integration Review

**Date:** 2026-07-07  
**Policy:** Clone new paths only — never overwrite existing VPS projects.

## Stack map

```text
ADVoi (/opt/advoi)           NEW — voice OS scaffold
    │ read-only bridge
    ▼
firstmate-fleet (/opt/firstmate-fleet)   LIVE — Grok captain, clapart active
    │ governance feed (lowest priority)
    ▼
aether (/opt/aether)           LIVE — principles canon, proactive cron
    │ active venture today
    ▼
gem-dev-shop (/opt/gem-dev-shop)   ACTIVE .aether/ venture (unchanged)

firstmate (/opt/firstmate)     LIVE legacy — AgentSim ops (untouched)
firstmate-pi-lab               LIVE — voice experiments (untouched)
hermes                         LIVE — Discord gateway
```

## Folder reviews

### `deployment/aather` → `/opt/aether`

| Item | Value |
|------|-------|
| Role | Principles OS, governance, `.aether/` sync |
| GitHub | `ActArtech/aether` |
| Cron | `5 */4 * * *` proactive cycle |
| Active venture | `gem-dev-shop` (do not switch without explicit decision) |
| ADVoi integration | Read governance JSON; bootstrap `.aether/` on advoi repo only |

### `deployment/firstmate` → `/opt/firstmate`

| Item | Value |
|------|-------|
| Role | Legacy AgentSim fleet (canonical + lab) |
| GitHub | `ActArtech/firstmate-ops` |
| Status | Up 7d, afk OFF |
| ADVoi | **Do not use** — fleet is the voice integration target |

### `deployment/firstmate-fleet` → `/opt/firstmate-fleet`

| Item | Value |
|------|-------|
| Role | Generic fleet — captain + crew, Discord/Hermes bridge |
| GitHub | `ActArtech/firstmate-fleet` (private) |
| Status | Up 4d, afk ON, active project **clapart** |
| ADVoi bridge | `scripts/fm-bridge.sh` → `fm-hermes-trigger.sh` |

## VPS insights applied

From `deployment/VPS-SETUP-INSIGHTS.md`:

- Traefik host-network — labels only, unique router names (`advoi-web`, `advoi-api`)
- DNS before SSL — grey cloud until LE cert issued
- Isolated compose project name `advoi`
- No port conflicts — PG/Redis on localhost high ports

## GitHub repos

| Repo | URL | VPS path |
|------|-----|----------|
| advoi-system | https://github.com/ActArtech/advoi-system | `/opt/advoi` (cloned) |
| aether | https://github.com/ActArtech/aether | `/opt/aether` |
| firstmate-fleet | https://github.com/ActArtech/firstmate-fleet | `/opt/firstmate-fleet` |
| firstmate-ops | https://github.com/ActArtech/firstmate-ops | `/opt/firstmate` |

## Verified on VPS (2026-07-07)

```bash
# ADVoi infra
docker compose -f /opt/advoi/docker-compose.yml --env-file /opt/advoi/deploy/.env ps

# Fleet bridge (read-only)
bash /opt/advoi/scripts/fm-bridge.sh "fleet status"

# Existing stacks untouched
docker ps | grep -E 'firstmate-fleet|firstmate-pi-lab|hermes|aether'
```