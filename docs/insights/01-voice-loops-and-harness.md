# Voice Loops, Harness & Confirmation

**Source:** `deployment/advoi/main1.txt`  
**Status:** Partially implemented in Stage 1

---

## Core thesis

Design **loops**, not prompts. A sustainable voice system needs a self-reinforcing cycle:

```
listen → understand (with context) → decide/act (with confirmation) → speak → update context
```

The **harness** is orchestration that prevents drift. **Context protocols** prevent collapse after 7–8 turns.

---

## Engineering layers

### Fast brain / slow brain

| Layer | Role |
|-------|------|
| Fast brain | Acknowledgments, fillers, turn-taking, interruptions — keeps voice flowing |
| Slow brain | Reasoning, tool calls, complex decisions in parallel |

Latency hiding: user hears *"Got it, checking that now"* while heavy work runs.

### Speculative tool calling

Kick off likely tools when partial intent is clear. Parse the stream aggressively. Wrong guesses are caught by the confirmation step.

### Context protocol

- Rolling window: last 3–5 turns + compressed summary of earlier context
- Inject only relevant runtime data (time, user state, session vars)
- Update summary asynchronously when window fills

### Confirmation harness

For **consequential actions**, force explicit verbal confirmation:

> "To confirm, you want X and Y — yes or no?"

Hard guardrail at top of prompt. Low-risk actions can be proactive.

---

## Six-section voice prompt template

Re-executed every turn; keep under ~500 tokens where possible:

1. **Identity & personality** — who ADVoi is, tone
2. **Response guidelines** — 1–2 sentences, one question at a time, natural speech (no markdown)
3. **Guardrails** — confirmation requirement overrides everything
4. **Context** — runtime-injected state
5. **Workflow** — step-by-step playbooks
6. **Examples** — few-shot ideal exchanges

Add **Tools** section with preambles: *"If calling a tool, first say a short acknowledgment."*

---

## Hermes + FirstMate integration (thin wrapper)

**Do not rewrite** Hermes, Paperclip, or FirstMate. Add a thin voice layer:

```
Mobile PWA → LiveKit → voice agent (STT/LLM/TTS)
                              ↓
                    FirstMate / fleet (Discord or webhook)
                              ↓
                    Voice summary back to user
```

ADVoi implements this as Pipecat + LiveKit with `fm-bridge.sh` for read-only fleet triggers.

---

## Advanced loops still needed

| Loop | Purpose | ADVoi status |
|------|---------|--------------|
| Memory loop | Post-session extract decisions → structured memory | Partial — recall at voice start; retain not wired |
| Hermes reflection | Every 30–60 min review progress vs goal | Not built |
| Protocol registry | Single source for decision frameworks | Stage 2 |
| Voice-state sync | Session focus, active framework, last 3 decisions | Redis stub |
| Escalation ladder | When to route to Hermes vs FirstMate | Not built |

---

## Decision frames (Stage 2)

Rejected **Lavish** (token-heavy, mobile friction). Preferred design:

- **Optionality every turn** — voice or button triggers
- **Decision Frame** — 2–3 options presented verbally or as PWA buttons
- **Confirmation loop** — always before execution
- **Deferred deep review** — complex HTML/visual prep for desktop, not live voice

Stage 1 ships disabled frame buttons in `VoiceSession.tsx`.

---

## Squad architecture (future)

Inspired by structured crew model:

| Role | Function |
|------|----------|
| Pathfinder | Research, discovery |
| Builder | Implementation |
| Foresight | Risk, alternatives |
| Sentinel | Quality, guardrails |
| Squad Leader | FirstMate-equivalent coordination |

Key rules from conversation:

- Squads push to staging at most
- High-impact actions require explicit confirmation
- 3-day silence rule before squad activation
- Escalation to Hermes when stuck

Mapped to `advoi/squads/` stub + fleet bridge.

---

## Mobile delivery decision

| Option | Verdict |
|--------|---------|
| Browser PWA | ✅ **Adopted** (ADR-001) — fastest path |
| React Native APK | Deferred |
| Native Kotlin | Deferred |

---

## Implementation pointers

| Insight | Code / doc |
|---------|------------|
| Confirmation | `ADVOI_CONFIRMATION_REQUIRED`, `advoi/voice/prompts.py` |
| Thin wrapper | `advoi/voice/agent.py`, `scripts/fm-bridge.sh` |
| Context window | `advoi/memory/redis_store.py` |
| Decision frames | `web/components/VoiceSession.tsx` (Stage 2) |