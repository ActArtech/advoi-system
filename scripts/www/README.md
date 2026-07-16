# www-tier scripts (three-tier VPS flow)

Canonical layout matches [docs/VPS-SETUP.md](../../docs/VPS-SETUP.md).

## Paths

| Tier | Path | Branch / role | Public URL |
|------|------|---------------|------------|
| **Develop** | `/data/projects/advoi` | Branch `develop` — integration checkout | — (no public host) |
| **Staging** | `/var/www/advoi/staging` | Promoted tree for pre-prod smoke | https://advoi-staging.keyteller.com |
| **Live** | `/var/www/advoi/live` | Production tree | https://advoi.keyteller.com |
| **Legacy** (deprecating) | `/opt/advoi` | Old single-path stack until cutover | historically `advoi.keyteller.com` |

Host promote entrypoints (optional install on VPS):

| Script | Host path |
|--------|-----------|
| `promote-to-staging.sh` (this directory) | `/var/www/advoi/promote-to-staging.sh` |
| `promote-to-live.sh` | **not in repo** — live cutover is out of scope here |

## Branch policy (avoid missed deploys)

| Ref | Role | Remote on GitHub? |
|-----|------|-------------------|
| `master` | Integration + VPS pull target (default) | yes (`origin/master`) |
| `develop` | Feature integration; must stay ff-aligned with `master` | yes (`origin/develop`) |
| `staging` | **Local VPS branch name only** in `/var/www/advoi/staging` | **no** — never `git pull origin staging` |

**What went wrong (2026-07-16):** `deploy-staging.sh` ran `git pull origin $(current-branch)`. On VPS the current branch was `staging`, but `origin/staging` does not exist. Compose restarted without fetching new commits from `master`.

**Correct routine (www tier, no develop checkout):**

```bash
bash /var/www/advoi/deploy-staging.sh
# internally: git fetch origin master && git checkout -B staging origin/master && compose up
```

**Correct routine (three-tier, develop checkout present):**

```bash
cd /data/projects/advoi && git pull origin develop
bash /var/www/advoi/promote-to-staging.sh
```

**Verify alignment:**

```bash
bash /var/www/advoi/staging/scripts/www/branch-policy-check.sh
# or: ADVOI_STAGING_DEPLOY_MODE=redeploy bash /var/www/advoi/deploy-staging.sh --check-only
```

| Variable | Default | Meaning |
|----------|---------|---------|
| `ADVOI_STAGING_DEPLOY_MODE` | `pull` | `pull` \| `promote` \| `redeploy` |
| `ADVOI_STAGING_DEPLOY_BRANCH` | `master` | Remote branch to fetch |
| `ADVOI_STAGING_LOCAL_BRANCH` | `staging` | Local branch name after pull |

Ship code: merge to `master`, fast-forward `develop` to the same SHA, then deploy.

## Operator prerequisite — GAP-013

**SSH host-key verification must succeed** for `deploy@` on the VPS before any remote promote or automated SSH deploy. If `known_hosts` / host key verification fails, fix that first; green T2 on the public staging URL only proves the currently deployed bootstrap tree, not develop tip parity.

This crewmate ship only vendors scripts into git. It does **not** SSH to the VPS or perform live cutover.

## Required environment

Documented defaults match the path table above. Override when paths differ.

| Variable | Default | Meaning |
|----------|---------|---------|
| `ADVOI_DEV_PATH` | `/data/projects/advoi` | Develop git checkout (source) |
| `ADVOI_STAGING_PATH` | `/var/www/advoi/staging` | Staging tree (target) |
| `ADVOI_DEPLOY_USER` | `deploy` | Expected OS user on the VPS |
| `ADVOI_DEV_BRANCH` | `develop` | Source branch name |
| `ADVOI_STAGING_BRANCH` | `staging` | Branch name in the staging tree |
| `ADVOI_ENV_FILE` | `$STAGING/deploy/.env` | Compose env file |
| `ADVOI_WWW_PROJECT` | `advoi-staging` | `COMPOSE_PROJECT_NAME` / compose `name` |
| `ADVOI_BASE_URL` | `https://advoi-staging.keyteller.com` | Post-promote smoke base |

No SSH private keys or host secrets belong in the repo or in these scripts.

## Promote develop → staging

On the VPS (as `deploy`), after develop has the desired tip:

```bash
# From develop checkout (or any checkout that has scripts/www/):
bash /data/projects/advoi/scripts/www/promote-to-staging.sh

# Dry-run (no git/compose mutation):
bash scripts/www/promote-to-staging.sh --dry-run

# Git only:
bash scripts/www/promote-to-staging.sh --skip-compose
```

Optional host install (once):

```bash
install -m 755 /data/projects/advoi/scripts/www/promote-to-staging.sh \
  /var/www/advoi/promote-to-staging.sh
bash /var/www/advoi/promote-to-staging.sh
```

Smoke:

```bash
curl https://advoi-staging.keyteller.com/api/health
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/t2-staging-smoke.sh
```

### What the script does

1. Fast-forwards the develop checkout (`ADVOI_DEV_PATH`, branch `develop`) when `origin` is available.
2. Ensures `/var/www/advoi/staging` is a **git** tree (clone-only; never rsync over non-git data).
3. Points the staging branch at the develop tip SHA (idempotent if already equal).
4. Runs compose with `docker-compose.yml` + `deploy/docker-compose.staging.yml` + root `compose.www.yml` under project `advoi-staging`.
5. Runs T2 smoke against `advoi-staging.keyteller.com` unless `--skip-smoke`.

## Compose overlay

Repo root: [`compose.www.yml`](../../compose.www.yml).

```bash
cd /var/www/advoi/staging
export COMPOSE_PROJECT_NAME=advoi-staging
export ADVOI_WWW_TIER=staging
docker compose \
  --env-file deploy/.env \
  -f docker-compose.yml \
  -f deploy/docker-compose.staging.yml \
  -f compose.www.yml \
  --profile app up -d
```

Set in `deploy/.env` for the staging tree:

- `STOREFRONT_HOST=advoi-staging.keyteller.com`
- Distinct `PROJECT_SLUG` if live and staging both run with Traefik (e.g. `advoi-staging` vs `advoi`) so router names do not collide.

Live cutover (`/var/www/advoi/live`, `promote-to-live.sh`) is **out of scope** for this package.

## Related docs

- [docs/VPS-SETUP.md](../../docs/VPS-SETUP.md) — three-tier layout
- [docs/operations/staging-runbook.md](../../docs/operations/staging-runbook.md) — deploy + smoke
- [docs/architecture/05-deployment-topology.md](../../docs/architecture/05-deployment-topology.md) — compose topology
