# Project Events

## Log

### 2026-07-07 — Stage 1 bootstrap

**Type:** lifecycle.sprint_start
**Priority:** high
**Source:** agent
**Stage:** Build
**Related decision:** ADR-001 Web PWA, ADR-002 LiveKit+Pipecat
**Triggers:** voice agent, web PWA, port registry, aether bootstrap
**Impact:** Stage 1 code paths landed in advoi-system
**Action required:** deploy app profile on VPS; verify LiveKit credentials
**Notes:** scripts/run-stage1-setup.sh

### 2026-07-07 — Memory stack (ADR-026)

**Type:** governance.decision
**Priority:** high
**Source:** aether
**Stage:** Build
**Related decision:** ADR-026 Hindsight ± Letta
**Triggers:** memory-setup-hindsight.sh
**Impact:** Hermes provider switched to hindsight on VPS
**Action required:** warm Hindsight embedded daemon
**Notes:** see docs/MEMORY-STACK.md