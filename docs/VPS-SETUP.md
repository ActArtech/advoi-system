# ADVoi VPS Setup — Aether Standard Order

**Mapping:** `1 slug = 1 GitHub repo = 1 Shelve project = 1 *.keyteller.com host = 1 .aether/`

| Slug | Repo | Path | Host | Shelve |
|------|------|------|------|--------|
| advoi | ActArtech/advoi-system | /opt/advoi | advoi.keyteller.com | ktteam/advoi/staging |

**Policy: clone only — never rsync over existing projects.**

---

## 8-step checklist

| Step | Action | ADVoi status |
|------|--------|--------------|
| 1 | Private GitHub repo `ActArtech/advoi-system` | ✅ Done |
| 2 | Deploy key on VPS → `github-advoi` in `~/.ssh/config` | Run `scripts/setup-vps-deploy-key.sh` |
| 3 | Clone **only** to `/opt/advoi` | `scripts/vps-bootstrap.sh` |
| 4 | Row in `/opt/shared/port-registry.md` | PG **5438**, Redis **6382** — see `deploy/port-registry-entry.md` |
| 5 | DNS A → `187.77.140.216` (grey cloud until LE) | `advoi.keyteller.com` |
| 6 | `deploy/.env` from staging example + Shelve `ktteam/advoi/staging` | `shelve.json` configured |
| 7 | Docker compose name `advoi` + Traefik `advoi-web` / `advoi-api` | `deploy/docker-compose.staging.yml` |
| 8 | Smoke: `curl -k -sI https://advoi.keyteller.com` → **200** | `scripts/vps-staging-check.sh` |

---

## Prerequisites

- VPS: `deploy@187.77.140.216`
- Traefik host-network (see `deployment/VPS-SETUP-INSIGHTS.md` in livekit-agent)
- DNS: `advoi.keyteller.com` → VPS IP (grey cloud until LE cert)

## One-time bootstrap

```bash
ssh deploy@187.77.140.216

# Step 2 — deploy key (first time only)
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ActArtech/advoi-system/master/scripts/setup-vps-deploy-key.sh)" 2>/dev/null \
  || bash scripts/setup-vps-deploy-key.sh
# Add pubkey to GitHub → advoi-system → Deploy keys (read-only)

# Step 3 — clone
git clone git@github-advoi:ActArtech/advoi-system.git /opt/advoi
cd /opt/advoi
bash scripts/vps-bootstrap.sh
```

If `/opt/advoi` already exists as git: bootstrap fast-forwards only.  
If `/opt/advoi` exists **without** `.git`: **stop** — manual rename required.

## Deploy

```bash
cd /opt/advoi
cp deploy/.env.staging.example deploy/.env   # if missing
nano deploy/.env                             # secrets, LiveKit, MEMORY_PROVIDER

# Infra (postgres + redis)
bash scripts/vps-deploy.sh

# Traefik routes (app profile)
DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app
bash scripts/vps-staging-check.sh
```

## Memory (ADR-026 — Hindsight first)

```bash
# On VPS — inside existing Hermes container
docker exec hermes hermes memory setup    # pick Hindsight

# Verify in deploy/.env:
# MEMORY_PROVIDER=hindsight
# HERMES_CONTAINER=hermes
```

See `docs/MEMORY-STACK.md` and `docs/LETTA-OPTIONAL.md`.

## Fleet bridge (read-only — no overwrite)

```bash
bash scripts/fm-bridge.sh "fleet status"
```

## Coexistence on VPS

| Path | Role |
|------|------|
| `/opt/advoi` | ADVoi app (this repo) |
| `/opt/hermes` | Hermes + Hindsight memory |
| `/opt/letta` | Optional v0.2 — separate compose |
| `/opt/firstmate-fleet` | Execution only; `fm-bridge.sh` read-only |
| `/opt/aether` | Governance canon; `.aether/` sync |

**Do not** put Letta/Hindsight data inside `/opt/firstmate-fleet`.

## Port registry

Add to `/opt/shared/port-registry.md` (copy from `deploy/port-registry-entry.md`):

| slug | path | host | PG host | Redis host |
|------|------|------|---------|------------|
| advoi | /opt/advoi | advoi.keyteller.com | 5438 | 6382 |