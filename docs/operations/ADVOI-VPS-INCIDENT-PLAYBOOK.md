# ADVoi VPS incident playbook (2026-07-10)

Lessons from staging promote failures, backlog drift, and false GitHub CI expectations.  
**Audience:** Captain + First Mate fleet. **Mode:** VPS-direct (no PR gate, no GitHub CI gate).

---

## 1. Issues faced (root cause)

| # | Symptom | Root cause | Cost |
|---|---------|------------|------|
| I1 | `ssh deploy@VPS: Host key verification failed` | Captain ran promote via **container SSH** to host | Promote parked; false GAP-013 for days |
| I2 | `git checkout` aborted on promote | **Dirty tree** on `/var/www/advoi/staging` (local edits) | Promote stalled |
| I3 | `deploy-staging.sh` failed after checkout | `deploy/docker-compose.www.yml` **not in git** | Manual copy needed each promote |
| I4 | Docker build failed on promote | `opentelemetry-instrumentation-fastapi>=0.48` — pip excludes beta tags | Need `>=0.48b0` |
| I5 | `reference is not a tree: <sha>` | Develop commit **local-only** on fleet; staging clone never fetched | Promote failed until `git fetch` |
| I6 | Backlog said "SSH blocked" while staging healthy | **Stale** `backlog.md` + `staging-state.md` + `gaps-and-blockers.md` | Captain idle / wrong dispatch |
| I7 | Items marked Done before staging deploy | Definition of done skipped **host promote + smoke** | False velocity |
| I8 | Captain waited on / pushed **GitHub CI** | `advoi-ci.yml` implies push gate; advoi is **VPS-direct** | Wasted turns; wrong blocker taxonomy |
| I9 | Duplicate backlog cards | Same id in Queued + Done + multiple `## Queued` sections | Wrong "next item" |

---

## 2. Prevention plan (mechanical)

### A. Promote path (never SSH from container)

| Do | Do not |
|----|--------|
| Host: `bash /var/www/advoi/promote-to-staging.sh` | `ssh deploy@187.77.140.216` from inside firstmate |
| Discord: **Deploy staging** button (`fm-fleet-bridge.py`) | Captain SSH to self |
| Log evidence in `data/feedback-evidence/<task-id>/` | Mark Done without smoke log |

**Preflight (before promote):**

1. Develop SHA: `git -C /opt/firstmate-fleet/data/projects/advoi rev-parse HEAD`
2. Staging clean: `git -C /var/www/advoi/staging status -sb` (stash if needed)
3. Required files in git: `deploy/docker-compose.www.yml`, `deploy/docker-compose.staging.yml`
4. Fetch local commits: promote script fetches fleet develop into staging (see hardening task)

**Postflight (definition of done):**

1. `ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh` exit 0
2. Update `data/staging-state.md` (develop SHA = staging SHA)
3. Update `docs/current-state/gaps-and-blockers.md` if P0 drift text changed
4. Backlog Done line includes staging SHA + smoke date

### B. GitHub / CI policy (advoi)

**ADVoi does not use GitHub Actions as a ship gate.**

| Tier | Gate | Where |
|------|------|-------|
| T0 | `uv run pytest tests/ -q` | Fleet develop `/data/projects/advoi` |
| T1 | Local smoke (optional) | Develop worktree |
| T2 | `staging-signoff-precheck.sh` | **VPS host** after promote |
| T3 | Human E2E | Phone per `E2E-SIGNOFF.md` |

- **Do not** push to GitHub per task.
- **Do not** open PRs or wait on `advoi-ci.yml` for advoi ship.
- **Do not** queue `fix-main-ci` or `gh-workflow-scope` blockers for advoi unless human requests archive push.
- `advoi-ci.yml` is **reference only** (workflow_dispatch) — not a fleet dependency.
- GitHub push = **archive mirror** when captain or human explicitly says so.

### C. Backlog hygiene (every promote or 5 Done)

1. One `## Queued` section — open items only at top.
2. `## merged-awaiting-deploy` — empty when staging aligned; never stale SHAs.
3. `blocked-by: ssh-*` — remove when host promote succeeds.
4. No duplicate task ids across Queued and Done.
5. Ship order header matches develop/staging SHAs from `staging-state.md`.

### D. Doc sync (batch gate)

When staging SHA changes, update in **one batch commit** on develop:

- `docs/current-state/gaps-and-blockers.md`
- `docs/current-state/SYSTEM-STATUS.md` (if present)
- `docs/current-state/ALIGNMENT-LOG.md`
- `data/staging-state.md` (fleet copy)

Stale current-state docs are **P0 quality debt** — they caused repeated GAP-013 false alarms.

### E. Dependency / build traps

| Trap | Prevention |
|------|------------|
| Pip pre-release versions (`>=0.48` vs `0.48b0`) | Pin beta suffix in `pyproject.toml`; T0 on develop before promote |
| Untracked compose overlays | Commit all `-f` files referenced in `deploy-staging.sh` |
| Local-only develop commits | Promote script `git fetch` fleet path; or push archive when human approves |

---

## 3. Captain directive (paste block)

See `data/captain.md` section **Advoi VPS-direct delivery (mandatory)** — fleet-private copy on VPS.

---

## 4. Backlog tasks (hardening)

| Id | Action |
|----|--------|
| `advoi-ops-promote-preflight-01` | Promote script: fetch fleet develop + preflight dirty tree |
| `advoi-ops-compose-git-01` | Commit `deploy/docker-compose.www.yml` on develop |
| `advoi-docs-current-state-sync-01` | gaps-and-blockers @ staging SHA |
| `advoi-ops-github-ci-policy-01` | `advoi-ci.yml` workflow_dispatch only; captain.md CI policy |

---

## 5. Escalation taxonomy (advoi)

| Label | Meaning | Fix |
|-------|---------|-----|
| `promote-host-only` | Tried container SSH | Host `promote-to-staging.sh` |
| `promote-dirty-tree` | Staging local edits | Stash/reset staging |
| `promote-missing-file` | Compose overlay not in git | Commit file on develop |
| `promote-build-deps` | Docker pip/npm fail | Fix on develop, re-promote |
| `doc-drift` | current-state stale | Batch doc sync |
| `github-ci-not-applicable` | Do not use for advoi | VPS T0/T2 only |

Never use `blocked-by: ssh-known-hosts` for advoi promote — use `promote-host-only` and fix in one host command.