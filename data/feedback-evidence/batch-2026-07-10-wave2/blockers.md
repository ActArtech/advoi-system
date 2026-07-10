# Parked blockers — wave 2 (2026-07-10)

## P0 — Staging VPS promote + OTEL apply

**Status:** Parked  
**Symptom:** SSH host key verification failed when attempting promote / redeploy  
**Staging SHA:** `5d50805`  
**Develop SHA:** `ce6a8e2`  

### Impact

- Cannot land wave2 code on advoi-staging  
- OTEL env + collector apply blocked (depends on redeploy)  
- M10.4 PEL row proof, beacon T2, guardian `trace_id` tail, aether proactive live — all blocked  
- T2 post-deploy script (`8584da3`) is ready but not re-executed against new tip  

### Unblock

1. Update `known_hosts` / verify host key for `deploy@` staging host (or jump host)  
2. `promote-to-staging.sh` or equivalent from develop tip `ce6a8e2` (or later)  
3. `bash scripts/t2-staging-smoke.sh` + `staging-signoff-precheck.sh`  
4. Set `OTEL_ENABLED=true` (+ collector); confirm `otel_ready` on platform diagnostics  
5. SQL proof for `portfolio_events` after fleet/frame/beacon  

### Non-blockers (still open, not SSH)

- M2 human E2E (device)  
- M5 live squad webhooks  
- M4.4 Letta  
- M7.2 full triage classifier  
