# Letta — Optional v0.2 Deployment

**Not required for Phase 1.** Start with Hindsight via Hermes (`docs/MEMORY-STACK.md`).

## When to add Letta

- Squad operational memory that self-edits over weeks
- Persistent ADVoi agent identity separate from portfolio beliefs
- MemFS git-backed archival memory

## VPS layout

```
/opt/letta/          ← separate clone, own compose (NOT inside advoi or fleet)
/opt/advoi/          ← LETTA_BASE_URL=http://letta:8283 on shared Docker network
/opt/hermes/         ← Hindsight unchanged
/opt/firstmate-fleet/ ← execution only — no memory
```

## Bootstrap (manual on VPS)

```bash
cd /opt
git clone https://github.com/letta-ai/letta.git letta
cd letta

# Follow upstream Docker docs — use unique host ports (register in port-registry.md)
# Example: LETTA_PORT=8283 (internal), no public expose — advoi reaches via Docker network

docker compose up -d
```

## ADVoi env

```env
LETTA_ENABLED=true
MEMORY_PROVIDER=both
LETTA_BASE_URL=http://letta:8283
LETTA_AGENT_ID=advoi-executive
```

## Boundaries (ADR-026)

| Write to Letta | Write to Hindsight |
|----------------|-------------------|
| User preferences | Portfolio facts |
| Squad lessons | Governance decisions |
| Workflow evolution | Cross-project synthesis |
| Agent identity | Venture beliefs |

## Backup

- Letta MemFS → git remote (daily cron)
- Do not store Letta volumes inside `/opt/firstmate-fleet`