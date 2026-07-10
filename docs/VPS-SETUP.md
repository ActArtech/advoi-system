# ADVoi VPS Setup — Aether Standard Order

**Mapping:** `1 slug = 1 GitHub repo = 1 Shelve project = 1 *.keyteller.com host = 1 .aether/`

| Slug | Repo | Shelve |
|------|------|--------|
| advoi | ActArtech/advoi-system | ktteam/advoi/staging |

**Policy: clone only — never rsync over existing projects.**

---

## Three-tier layout (canonical, 2026-07-10)

ADVoi on the VPS uses a **develop → staging → live** path model. Staging is **not** only at `/opt/advoi`.

| Tier | Path | Branch / role | Public URL |
|------|------|---------------|------------|
| **Develop** | `/data/projects/advoi` | Branch `develop` — active git worktree / integration checkout | — (no public host) |
| **Staging** | `/var/www/advoi/staging` | Promoted tree served for pre-prod smoke | https://advoi-staging.keyteller.com |
| **Live** | `/var/www/advoi/live` | Production tree | https://advoi.keyteller.com |
| **Legacy** (deprecating) | `/opt/advoi` | Old single-path stack until cutover | historically `advoi.keyteller.com` |

### Promote develop → staging

On the VPS (host script; not checked into this repo as of 2026-07-10):

```bash
bash /var/www/advoi/promote-to-staging.sh
```

Smoke after promote:

```bash
curl https://advoi-staging.keyteller.com/api/health
```

Optional full staging check (legacy `/opt/advoi` tooling still works where the old stack is running):

```bash
bash scripts/vps-staging-check.sh
# Prefer staging hostname when www tier is live:
# ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/agents-smoke-test.sh
```

### Repo gap (docs only)

- **`scripts/www/`** — not present in this repository.
- **`promote-to-staging.sh`** — lives on the VPS at `/var/www/advoi/promote-to-staging.sh`; not vendored here. Do not invent a repo copy until ops lands one.

### Legacy path (`/opt/advoi`)

`/opt/advoi` remains on disk for the old compose/Traefik stack during cutover. New installs and day-to-day promote flow should use the www tiers above. Bootstrap scripts (`scripts/vps-bootstrap.sh`, `scripts/vps-deploy.sh`) still default to `/opt/advoi` until they are retargeted — treat those defaults as **legacy**.

---

## 8-step checklist (new installs)

Use this for a greenfield VPS bring-up aligned with the three-tier model. Steps that still run under the legacy path are marked.

| Step | Action | ADVoi status / notes |
|------|--------|----------------------|
| 1 | Private GitHub repo `ActArtech/advoi-system` | ✅ Done |
| 2 | Deploy key on VPS → `github-advoi` in `~/.ssh/config` | Run `scripts/setup-vps-deploy-key.sh` |
| 3 | Clone develop checkout to `/data/projects/advoi` (branch `develop`) | Prefer www model; legacy clone was `/opt/advoi` via `scripts/vps-bootstrap.sh` |
| 4 | Row in `/opt/shared/port-registry.md` | PG **5438**, Redis **6382** — see `deploy/port-registry-entry.md` |
| 5 | DNS A → `187.77.140.216` (grey cloud until LE) | **Staging:** `advoi-staging.keyteller.com` · **Live:** `advoi.keyteller.com` |
| 6 | `deploy/.env` from staging example + Shelve `ktteam/advoi/staging` | `shelve.json` configured |
| 7 | Docker compose name `advoi` + Traefik labels for web/api (and staging host) | `deploy/docker-compose.staging.yml`; stage host `advoi-staging.keyteller.com` |
| 8 | Smoke | `curl https://advoi-staging.keyteller.com/api/health` → healthy JSON; live: `curl -k -sI https://advoi.keyteller.com` → **200** |

---

## Prerequisites

- VPS: `deploy@187.77.140.216`
- Traefik host-network (see `deployment/VPS-SETUP-INSIGHTS.md` in livekit-agent)
- DNS:
  - `advoi-staging.keyteller.com` → VPS IP (grey cloud until LE cert)
  - `advoi.keyteller.com` → VPS IP (live)

## One-time bootstrap

### Preferred (three-tier)

```bash
ssh deploy@187.77.140.216

# Step 2 — deploy key (first time only)
bash -c "$(curl -fsSL https://raw.githubusercontent.com/ActArtech/advoi-system/master/scripts/setup-vps-deploy-key.sh)" 2>/dev/null \
  || bash scripts/setup-vps-deploy-key.sh
# Add pubkey to GitHub → advoi-system → Deploy keys (read-only)

# Step 3 — develop checkout
git clone git@github-advoi:ActArtech/advoi-system.git /data/projects/advoi
cd /data/projects/advoi
git checkout develop
# Install / env / compose per ops; promote with:
# bash /var/www/advoi/promote-to-staging.sh
```

Ensure host dirs exist for promote targets:

```text
/var/www/advoi/staging   # staging tree
/var/www/advoi/live      # live tree
/var/www/advoi/promote-to-staging.sh
```

### Legacy bootstrap (`/opt/advoi` — deprecating)

```bash
git clone git@github-advoi:ActArtech/advoi-system.git /opt/advoi
cd /opt/advoi
bash scripts/vps-bootstrap.sh
```

If `/opt/advoi` already exists as git: bootstrap fast-forwards only.  
If `/opt/advoi` exists **without** `.git`: **stop** — manual rename required.

## Deploy

### Staging (www flow)

```bash
# From develop work, then promote on VPS:
bash /var/www/advoi/promote-to-staging.sh
curl https://advoi-staging.keyteller.com/api/health
```

### Legacy compose deploy (still valid on `/opt/advoi` until cutover)

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
| `/data/projects/advoi` | Develop checkout (branch `develop`) |
| `/var/www/advoi/staging` | Staging www tree → `advoi-staging.keyteller.com` |
| `/var/www/advoi/live` | Live www tree → `advoi.keyteller.com` |
| `/opt/advoi` | **Legacy** app tree (deprecating; old stack until cutover) |
| `/opt/hermes` | Hermes + Hindsight memory |
| `/opt/letta` | Optional v0.2 — separate compose |
| `/opt/firstmate-fleet` | Execution only; `fm-bridge.sh` read-only |
| `/opt/aether` | Governance canon; `.aether/` sync |

**Do not** put Letta/Hindsight data inside `/opt/firstmate-fleet`.

## Port registry

Add to `/opt/shared/port-registry.md` (copy from `deploy/port-registry-entry.md`):

| slug | path | host | PG host | Redis host |
|------|------|------|---------|------------|
| advoi | `/data/projects/advoi` (dev); staging/live under `/var/www/advoi/*` | advoi-staging.keyteller.com / advoi.keyteller.com | 5438 | 6382 |
| advoi (legacy) | `/opt/advoi` | advoi.keyteller.com (old stack) | 5438 | 6382 |
