# AI-Native SaaS Principles

**Source:** `deployment/advoi/newaistanderd.txt`  
**Status:** Governs product philosophy in CLARITY-FRAMEWORK

---

## Core belief

We are no longer building software — we are building **intelligence**. Fast has evolved; iteration velocity + distribution + customer obsession are the new defensibility.

---

## Three principles

### 1. Mode = intelligence layer, not UI

- Stop obsessing over pixel-perfect dashboards — AI generates UI in minutes
- **Moat:** proprietary data, distribution, deeply embedded workflows
- Product must **learn from every interaction** — if it doesn't improve with usage, it's obsolete

**ADVoi mapping:** Voice + memory (Hindsight) + fleet integration are the moat; PWA is thin shell.

### 2. Ship capabilities & outcomes, not features

Replace *"What features next?"* with:

> What task should the system autonomously complete for the user?

- Think in **agents**, not feature lists
- Sell **completed outcomes**, not tools
- Minimal friction, maximum autonomy

**ADVoi mapping:** Stage 1 outcome = *"Hear portfolio status and trigger fleet actions by voice with confirmation."*

### 3. Speed is the new defensibility

- AI collapsed build cost — competitors appear overnight
- Advantage = iteration velocity + distribution + customer obsession
- Living system that improves daily

**ADVoi mapping:** 3-day Stage 1 appetite in `.aether/BET.md`; ship voice path before decision frames.

---

## Design implications for ADVoi

| Principle | Implementation choice |
|-----------|----------------------|
| Intelligence > UI | Web PWA not native app (ADR-001) |
| Outcomes | Voice session completes a portfolio check, not a chat feature |
| Learning | Hindsight retain/recall; Letta v0.2 for operational learning |
| Speed | Thin wrapper over existing Hermes/fleet — no rewrite |

---

## Anti-patterns (from combined sources)

- Building beautiful dashboards before voice + memory work
- Feature lists without autonomous task completion
- Static prompts that don't improve from logged failures
- Lock-in tools (Coolify, Lavish) over owned VPS + git-backed state