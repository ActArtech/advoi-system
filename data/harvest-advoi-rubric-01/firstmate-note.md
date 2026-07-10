# Firstmate note — harvest-advoi-rubric-01

**Date:** 2026-07-10  
**Branch:** `fm/harvest-advoi-rubric-01` (from `origin/develop` @ `bb31f4c`)  
**Repo deliverables (crewmate):**  
- `docs/operations/HARVEST-RUBRIC-ADVOI.md` — canonical ADVoi scout lenses + parser-compatible report template  
- Links from `docs/operations/README.md` and `docs/operations/BATCH-DOCUMENTATION.md`  

**Crewmate does not write** `/data/config/harvest-rubric.md` or `/data/config/harvest-mode.md` — firstmate owns fleet config.

---

## Why

Fleet `harvest-mode.md` has `target: advoi` but `/data/config/harvest-rubric.md` still describes **agentsim-lab** (assess funnel, lab URL, JMTS). Scouts for ADVoi inherit wrong discovery heuristics. Baseline harvest report (`advoi-harvest-baseline-01`) flagged this as value-7 ARCH gap.

---

## Merge instructions (firstmate)

### 1. Merge repo branch → develop (VPS-direct, no PR)

```bash
cd /data/projects/advoi
git fetch origin
git checkout develop
git merge --ff-only fm/harvest-advoi-rubric-01
# push if this host tracks origin/develop
```

### 2. Replace fleet harvest rubric with ADVoi content

**Source of truth in git:** `/data/projects/advoi/docs/operations/HARVEST-RUBRIC-ADVOI.md`  
**Fleet runtime path:** `/data/config/harvest-rubric.md`

```bash
# Backup agentsim-era copy once
cp -a /data/config/harvest-rubric.md /data/config/harvest-rubric.md.bak-agentsim-$(date -u +%Y%m%d)

# Install ADVoi rubric (full file replace — do not leave agentsim primary walk URLs)
cp /data/projects/advoi/docs/operations/HARVEST-RUBRIC-ADVOI.md /data/config/harvest-rubric.md
```

Optional multi-project layout (if clapart/agentsim still need their own rubrics later):

```text
/data/config/harvest-rubric.md           # default / active project
/data/config/harvest-rubric-advoi.md     # symlink or copy of repo HARVEST-RUBRIC-ADVOI.md
/data/config/harvest-rubric-agentsim.md  # restored from .bak when scouting lab
```

Until spawn scripts support `harvest-rubric-${FM_ACTIVE_PROJECT}.md`, keep **active** file ADVoi-flavored while `target: advoi`.

### 3. Update `harvest-mode.md` rotate lenses (recommended)

Edit `/data/config/harvest-mode.md`:

```yaml
# Prefer product lenses (repo rubric headings). Custom names default lane OPP unless card sets lane:.
rotate_lenses: ingest-lifecycle,voice-pwa,aether-pel,fleet-bridge,staging-smoke,memory-adr026,ontology
```

**Compat alternative** (if spawn/tooling must stay on classic five):

```yaml
rotate_lenses: validate,architecture,ux,refactor,feature
```

Classic five remain as `## validate (VAL)` … sections in the ADVoi rubric (mapped to product surfaces). Product seven are preferred for signal quality.

Confirm still:

```yaml
target: advoi
min_value_to_queue: 6
max_complexity_auto_dispatch: M
report_dir: data/harvest-reports
```

### 4. Smoke the contract (no full scout required)

```bash
# Headings present for spawn + parser template
grep -E '^## (ingest-lifecycle|voice-pwa|aether-pel|fleet-bridge|staging-smoke|memory-adr026|ontology|validate|Executive summary|Findings|Top 3)' \
  /data/config/harvest-rubric.md

# No agentsim primary walk left in active rubric
! grep -n 'agentsim-lab.keyteller.com' /data/config/harvest-rubric.md || echo "WARN: agentsim URL still present (anti-pattern unless explicitly secondary)"
```

Expected: product + alias lens headings; report template with **Executive summary**, **Findings (table)**, **Top 3 ship candidates** (`value:`, `complexity:`, `lane:`, `repo: advoi`).

### 5. Next harvest cycle

After merge + config install, next `fm-harvest-wake` / `fm-spawn-harvest-scout.sh` for advoi should brief scouts against ADVoi surfaces (staging PWA, ingestion lifecycle, aether/PEL, fleet bridge, ADR-026 memory, ontology). Ingest path unchanged: `data/<scout-id>/report.md` → `harvest-ingest-report.sh` → `/data/harvest-backlog-advoi.md` → promote → `backlog.md`.

---

## Acceptance checklist (firstmate)

- [ ] Branch `fm/harvest-advoi-rubric-01` merged to `develop`
- [ ] `/data/config/harvest-rubric.md` is ADVoi-on-product (not agentsim primary)
- [ ] `rotate_lenses` either product seven or classic five with ADVoi body under those headings
- [ ] Parser sections preserved (Executive summary / Findings table / Top N cards with value+complexity)
- [ ] Mark fleet task `harvest-advoi-rubric-01` **Done** (config write is the close criterion)

---

## Explicit non-goals (crewmate)

- Did **not** edit `/opt/firstmate/scripts/harvest-*.sh` (project-aware cycle-report HB path remains a separate ARCH ship if still hardcoded to agentsim).
- Did **not** open a PR (VPS-direct firstmate merge).
- Did **not** spawn a live harvest scout or mutate `/data/backlog.md`.
