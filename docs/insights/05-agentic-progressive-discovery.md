# Agentic Progressive Discovery

**Source:** `deployment/advoi/aganticall.txt`  
**Status:** Reference for routing/squad quality loops; not yet implemented

---

## Core problem

LLMs are next-token predictors — they converge on **local optima** (first coherent answer wins). Without scaffolding:

- Surface-level agreement with user framing
- Missed alternatives until later conversation turns
- No exhaustive comparison or backtracking

---

## Immediate prompting fixes

### Demand exploration

> Evaluate 5+ options including lesser-known ones. Score against stack and constraints. Rank by optimality. Critique your own recommendation.

### Iterative refinement

Multi-turn: generate → critique assumptions → improve → repeat until convergence (3–4 rounds).

### Advanced structures

| Pattern | Use |
|---------|-----|
| Chain-of-Thought | Step-by-step decomposition |
| Tree-of-Thoughts | Branch, evaluate, prune, expand |
| Graph-of-Thoughts | Merge ideas, backtrack, non-linear |
| Role + constraints | Senior architect persona, ruthless about optimality |

---

## Progressive optimizer agent (architecture)

```
Orchestrator
  ├── Generator agents (diverse candidates)
  ├── Critic/evaluator agents (score vs criteria)
  ├── Refiner (merge best, backtrack weak paths)
  ├── Memory/verifier (avoid cycles, tool grounding)
  └── Termination (convergence or budget)
```

**Reference repo:** `all-agentic-architectures` — 35 modular patterns (Reflection, Reflexion, Self-Discover, CoVe, Self-RAG) with uniform `.run(task)` interface.

---

## Frameworks

- LangGraph (stateful, extensible)
- CrewAI / AutoGen
- MARS, PromptWizard, Self-Refine, ARTS for tree search

For GitHub selection: agent searches repos, clones/evals, benchmarks against stack.

---

## Limitations

- Self-verification unreliable without external signals
- Compute cost scales with depth
- Hallucinations in deep search — **ground with tools**

---

## ADVoi application

| Use case | Where it fits |
|----------|---------------|
| Tech/repo selection for squads | `advoi/squads/` future |
| Model routing decisions | `advoi/routing/` stub |
| Architecture reviews | Aether reflection loop |
| Voice quality meta-loop | Guardian + prompt patch cycle |

**Stage 1:** not active. **Stage 2+:** wrap high-stakes fleet triggers in Reflexion loop before execution.

---

## Starter system prompt (adapted)

For tech/architecture decisions routed through ADVoi:

1. Decompose into constraints and success metrics
2. Generate 4–6 diverse solutions (common + novel)
3. Critique each (pros/cons, risks, score 1–10)
4. Synthesize best hybrid or recommend top with path
5. Self-critique final output
6. Prioritize long-term value over quick wins