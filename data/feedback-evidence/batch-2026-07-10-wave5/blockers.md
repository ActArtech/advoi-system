# Parked blockers — wave 5 (2026-07-10)

## P0 — Staging VPS promote (SSH host key) — GAP-013

**Status:** Parked (carried from wave 2 → 3 → 4 → staging-record → ops-review → tip `9065b94`)  
**Symptom:** SSH host key verification failed when attempting promote / redeploy  
**Staging SHA:** `5d50805`  
**Develop SHA:** `9065b94`  

### Impact

- Cannot land wave 5 (or wave 2–4) ships on advoi-staging  
- review_queue PG durability, retain metrics, TTL retention, triage/ingest UI, wake_firstmate bridge, www promote path unproven on VPS tip  
- A14–A17 human checks on staging tip still blocked (device tests against bootstrap-era code invalid for post-wave2 surfaces)  
- M10.4 PEL row proof, analytics funnel SQL, gate_snapshot PEL emit T2, OTEL apply still blocked  
- Versioned SQL migrations + paperclip ingest field not on VPS  
- T2 post-deploy script ready but not re-executed against tip `9065b94`  

### Unblock

1. Update `known_hosts` / verify host key for `deploy@` staging host (or jump host) — **GAP-013**  
2. `promote-to-staging.sh` (or www three-tier promote) from develop tip `9065b94` (or later wrap-up SHA)  
3. `bash scripts/t2-staging-smoke.sh` + `staging-signoff-precheck.sh` with `ADVOI_BASE_URL=https://advoi-staging.keyteller.com`  
4. Optional: set `OTEL_ENABLED=true` (+ collector); confirm `otel_ready` + guardian JSONL trace correlation  
5. SQL proof for `portfolio_events`, `review_queue`, memory_events retention after promote  
6. Install/enable aether feed cron + gate export on VPS if not already wired  

### Non-blockers (still open, not SSH)

- M2 human E2E A11–A17 (device)  
- M5 live squad webhooks  
- M4.4 Letta  
- M7 Phase 2 full batch upload / advanced inbox (explicit deferred complexity L)  
- M3.5 full Playwright connect smoke  
- Write-path audit V4 (voice imports fleet) / V5 (aether fleet-tree publish) — P1/P2 deferred  
