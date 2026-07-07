# Pipecat, LiveKit & Executive OS Stack

**Source:** `deployment/advoi/main2.txt`  
**Status:** Stage 1 voice path implemented

---

## Vision

Voice-first executive system: spoken intent → research, planning, architecture, portfolio alignment, publishing — without keyboard unless desired.

No commercial platform delivers this end-to-end today. Closest pieces: Retell, Vapi, Lindy — but not personal VPS-backed executive architect. **Custom build on Pipecat + existing stack.**

---

## Pipecat vs LiveKit (caveman model)

| Component | Role |
|-----------|------|
| **LiveKit** | The road — carries voice fast between phone and server |
| **Pipecat** | The driver — STT → LLM → tools → TTS, the brain and hands |

LiveKit alone = fancy phone call with no intelligence.  
Pipecat alone = brain without reliable transport.  
**Together:** LiveKit transport + Pipecat pipeline (ADVoi Stage 1).

---

## Full stack (conversation model)

```
┌─────────────────────────────────────┐
│  Ontology layer (definitions,       │
│  operating procedures, success)     │
├─────────────────────────────────────┤
│  Orchestrator / Executive layer     │
│  (goal → plan → priority)           │
├─────────────────────────────────────┤
│  Function calling layer             │
│  (atomic tools on VPS)              │
├─────────────────────────────────────┤
│  Execution layer                    │
│  Hermes, fleet, data, publish hooks │
└─────────────────────────────────────┘
```

Raw function calling is insufficient without ontology + orchestrator — system must understand *what* portfolio priority means, not just execute commands.

---

## Function calling — top 10 principles

1. **Atomic tools** — one clear action per function
2. **Crystal-clear descriptions** — LLM reads these like a manual
3. **Strict parameter schemas** — types, required vs optional
4. **Validate inputs** — never trust LLM output directly
5. **Clean error handling** — errors the LLM can recover from
6. **Limit tools per call** — group logically or use a router
7. **Final answer tool** — explicit "I'm done" signal
8. **Observable tools** — log every call, input, result
9. **Parallel tool calling** — independent tools in parallel
10. **State and memory** — tools read/update portfolio structures

ADVoi Stage 1: token endpoint + health only. Tool surface expands in Stage 2+.

---

## FirstMate ecosystem

FirstMate (kunchenguid) = captain orchestrator:

- Spawns specialized crewmates in isolated git worktrees
- Bash watcher wakes captain only when decisions needed
- Observable tmux sessions
- Strong safety — no random main-branch changes

ADVoi connects via **read-only** `fm-bridge.sh` — does not overwrite fleet config.

---

## Platform comparisons (from conversation)

| Platform | Strength | Gap for ADVoi use case |
|----------|----------|------------------------|
| Lindy AI | Prompt → multi-tool automation | Not personal VPS executive |
| Pipecat | Pipeline + tool calling + self-host | Need executive layer on top |
| Bolna | Lighter, faster prototype | Smaller community |
| Wispr Flow | Voice dictation ($700M val) | Input only, no actions |
| AgentVoice / Retell | Business phone automation | Not portfolio architect |

---

## Mobile & delivery

Conversation explored React Native APK → **final decision: Web PWA first** (see ADR-001).

PWA: mic permission, installable shell, LiveKit web client — no store required.

---

## ADVoi mapping

| Conversation concept | Implementation |
|---------------------|----------------|
| Pipecat pipeline | `advoi/voice/agent.py` |
| LiveKit transport | `LiveKitTransport`, token API |
| VPS always-on agent | `advoi-voice` container, `restart: unless-stopped` |
| Existing data/structures | Hermes, fleet, postgres — not replaced |
| Orchestrator layer | `advoi/aether/` stub (future) |
| Function tools | Stage 2+ via routing module |