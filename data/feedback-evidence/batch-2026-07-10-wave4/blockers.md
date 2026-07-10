# Parked blockers — wave 4 (2026-07-10)

## P0 — Staging VPS promote (SSH host key)

**Status:** Parked (carried from wave 2 → 3 → 4; still open)  
**Symptom:** SSH host key verification failed when attempting promote / redeploy  
**Staging SHA:** `5d50805`  
**Develop SHA:** `61de279`  

### Impact

- Cannot land wave 4 Aether/arch ships on advoi-staging  
- Gate-required feed cron, atomic publish, gate export, write-path hard-gate unproven on VPS tip  
- A14–A17 human checks on staging tip still blocked (device tests against bootstrap-era code invalid for post-wave2 surfaces)  
- M10.4 PEL row proof, analytics funnel SQL, gate_snapshot PEL emit T2, OTEL apply still blocked  
- T2 post-deploy script (`8584da3`) ready but not re-executed against tip `61de279`  

### Unblock

1. Update `known_hosts` / verify host key for `deploy@` staging host (or jump host)  
2. `promote-to-staging.sh` or equivalent from develop tip `61de279` (or later wrap-up SHA)  
3. `bash scripts/t2-staging-smoke.sh` + `staging-signoff-precheck.sh`  
4. Optional: set `OTEL_ENABLED=true` (+ collector); confirm `otel_ready`  
5. SQL proof for `portfolio_events` after fleet/frame/beacon/gate_export; run funnel stage queries from `docs/operations/ANALYTICS-FUNNEL.md`  
6. Install/enable `aether-feed-cron` + `aether-gate-export` on VPS if not already wired  

### Non-blockers (still open, not SSH)

- M2 human E2E A11–A17 (device)  
- M5 live squad webhooks  
- M4.4 Letta  
- M7.2 full triage classifier / inbox UI / batch upload  
- M3.5 full Playwright connect smoke (stubs exist)  
- Write-path audit V4 (voice imports fleet) / V5 (aether fleet-tree publish) — P1/P2 deferred  
