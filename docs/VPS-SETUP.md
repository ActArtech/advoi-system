# ADVoi VPS Setup

**Policy: clone only — never overwrite existing `/opt/*` projects.**

| Path | Action |
|------|--------|
| `/opt/advoi` | Fresh clone of `ActArtech/advoi-system` |
| `/opt/firstmate-fleet` | Read-only bridge via `scripts/fm-bridge.sh` |
| `/opt/aether` | Governance read-only (when `.aether/` bootstrapped) |
| `/opt/firstmate` | Legacy — do not touch |

## Prerequisites

- VPS: `deploy@187.77.140.216`
- Traefik host-network (see `deployment/VPS-SETUP-INSIGHTS.md`)
- DNS: `advoi.keyteller.com` → VPS IP (grey cloud until LE cert)
- GitHub deploy key: `github-advoi` → `ActArtech/advoi-system`

## One-time bootstrap

```bash
ssh deploy@187.77.140.216
cd /opt/advoi 2>/dev/null || true

# If /opt/advoi does not exist yet:
git clone git@github-advoi:ActArtech/advoi-system.git /opt/advoi
cd /opt/advoi
bash scripts/setup-vps-deploy-key.sh   # first time only — add pubkey to GitHub
bash scripts/vps-bootstrap.sh
```

If `/opt/advoi` already exists as git: bootstrap only fast-forwards (`git merge --ff-only`).

If `/opt/advoi` exists without `.git`: **stop** — manual rename required (no overwrite).

## Deploy

```bash
cd /opt/advoi
cp deploy/.env.staging.example deploy/.env   # if missing
nano deploy/.env                             # secrets, LiveKit, API keys

# Infra only (postgres + redis)
bash scripts/vps-deploy.sh

# With Traefik routes (when app profile ready)
DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app
bash scripts/vps-staging-check.sh
```

## Fleet bridge (no overwrite)

```bash
bash scripts/fm-bridge.sh "fleet status"
bash scripts/fm-bridge.sh "fleet work <task for clapart or active project>"
```

## Port registry

Add to `/opt/shared/port-registry.md`:

| slug | path | staging host | notes |
|------|------|--------------|-------|
| advoi | /opt/advoi | advoi.keyteller.com | PG host 5434, Redis 6381 |