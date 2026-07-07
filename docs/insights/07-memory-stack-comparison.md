# Memory Stack Comparison

**Source:** `deployment/advoi/gstak tenet.txt`  
**Status:** ADR-026 locked — Hindsight first via Hermes

---

## One-line definitions

| System | One sentence |
|--------|--------------|
| **G-Stack** | Prompt-based workflow turning Claude into engineering team with sprint roles |
| **G-Brain** | Git-backed Markdown knowledge base with graph, hybrid search, nightly dream cycle |
| **Hindsight** | Structured multi-layer memory that synthesizes facts into observations and mental models |
| **Letta (Leda)** | Self-editing agent memory with persistent identity and sleep-time learning |
| **Mnemosyne** | Fast local 3-tier memory (working, episodic, long-term) in single SQLite file |
| **Ladybug** | Lightweight local Hermes plugin, importance-weighted, zero cloud |

---

## When to use each

| System | Best for |
|--------|----------|
| **Mnemosyne** | Local, fast, single-user, offline, low overhead |
| **Hindsight** | Complex agents that learn over time; governance + synthesis |
| **Letta** | Long-running agents with identity across weeks/months |
| **G-Stack + G-Brain** | Solo builders in Claude Code wanting git-owned brain + sprint process |
| **Graphify** | Codebase structural graph — noisy at scale without filtering |
| **Nexus** | Decision graph for multi-agent alignment — sprawl risk |

---

## Senior dev critique (validated)

- G-Stack = curated prompts; many seniors already have private equivalents
- G-Brain = self-maintaining library, not true agent memory; ops overhead at scale
- Graphify / Nexus = capture-everything → **clutter and chaotic graphs**
- Hindsight = benchmark leader for long-term reasoning, native in Hermes

---

## ADVoi decision (ADR-026)

```
Voice / ADVoi routing
    ├── Hindsight (via Hermes)  → portfolio facts, decisions, governance
    ├── Letta (v0.2 optional)   → agent identity, operational learning
    ├── PostgreSQL              → canonical structured state
    └── Redis                   → ephemeral last 3–5 turns
```

**Rule:** Hindsight = what the system knows. Letta = who the agent is. Postgres = records. Guardian log = failures only.

---

## Newer alternatives mentioned (evaluate, not adopted)

| System | Claim |
|--------|-------|
| **Memora** | Low-noise abstractions, 98% fewer tokens vs raw graphs |
| **Kumiho** | Scoped workflow views, immutable revisions, dream-state cleanup |
| **EverOS** | Self-evolving skills from trajectories |

**Complement Graphify:** Kumiho spaces (`/workflow/sales`, `/system/architecture`) for filtered views — deferred.

---

## Rejected for ADVoi

| Tool | Reason |
|------|--------|
| Nexus | Cluttered decision graphs |
| Graphify as primary | Noisy; keep as complement only |
| G-Stack as memory | Workflow layer, not memory |
| Cognee + everything at once | Pick one stack (this one) |

---

## VPS setup

```bash
bash /opt/advoi/scripts/memory-setup-hindsight.sh
# MEMORY_PROVIDER=hindsight in deploy/.env
bash scripts/memory-health.sh   # after daemon warm
```

See [MEMORY-STACK.md](../MEMORY-STACK.md).