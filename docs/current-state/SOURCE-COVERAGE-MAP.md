# Source coverage map

**Date:** 2026-07-08  
**Sources reviewed:** `ontology.txt`, `aganticall.txt`, `main1.txt`, `main2.txt`  
**Canonical synthesis:** `docs/CLARITY-FRAMEWORK.md`  
**Build state:** Build 1.5 (voice + PWA + 3 agents)

Legend: **Done** | **Partial** | **Mapped only** (spec/decision, not code) | **Gap** (not captured)

---

## 1. ontology.txt — Strategy Stack & formal ontology

| Concept | Mapped in docs? | Implemented in code? | Where |
|---------|-----------------|----------------------|-------|
| Strategy Stack (Purpose → Object) | Yes | Mapped only | `CLARITY-FRAMEWORK.md` §2 |
| Motivation, Appetite, Capacity | Yes | Gap | Harness guardrails not wired |
| Impact, Outcome, JTBD | Yes | Mapped only | §2.1; no KPI ontology in DB |
| Events as first-class | Yes | Partial | `memory_events`, review queue; no OWL |
| Named multi-relationships | Yes | Mapped only | Design principle; no graph store |
| Solutions vs Objects/Assets | Yes | Partial | Frames = solutions; fleet slug = project object |
| Agentic harness ↔ stack layers | Yes | Partial | Prompts + confirm; no policy engine |
| Layered ontology (upper/core/vertical) | Yes | Mapped only | Verticals in §3.2; no Protégé/ROBOT |
| MCP-native ontology tools | Yes | Gap | Referenced; not integrated |
| OO/UX alignment from ontology | Yes | Partial | Frame labels + voice_prompt shared catalog |

**Verdict:** Fully **mapped** in CLARITY-FRAMEWORK. **Not implemented** as formal OWL/SHACL or schema generation pipeline.

---

## 2. aganticall.txt — Progressive discovery & agentic loops

| Concept | Mapped in docs? | Implemented in code? | Where |
|---------|-----------------|----------------------|-------|
| Reflexion / self-critique loops | Yes | Gap | `insights/05-agentic-progressive-discovery.md` |
| Generator + Critic + Refiner orchestrator | Yes | Gap | Future: Hermes reflection, Aether CI loop |
| all-agentic-architectures patterns | Yes | Gap | Reference repo only |
| ToT / GoT reasoning structures | Yes | Gap | Not in voice pipeline |
| Deterministic scoring vs LLM agree | Yes | Partial | Priority Engine concept only (main1) |
| Progressive optimizer for tech choices | Yes | Gap | Manual / Hermes today |

**Verdict:** **Mapped** as reference for Phase 4 quality loops. **Not built** in ADVoi runtime.

---

## 3. main1.txt — Voice harness, decisions, squads, portfolio

### 3.1 Voice loop & harness

| Concept | Status | Evidence |
|---------|--------|----------|
| listen → understand → confirm → speak → context | Partial | Pipecat pipeline; confirm on Option C only |
| Fast brain / slow brain | Mapped only | `insights/01`; no filler TTS layer |
| Speculative tool calling | Gap | Not in voice agent |
| Rolling context window (3–5 turns) | Partial | `redis_store`, `memory_hooks`; no summary compressor |
| Six-section voice prompt template | Partial | `prompts.py` (identity, guidelines); not full 6-block |
| Confirmation harness (consequential actions) | Partial | `ADVOI_CONFIRMATION_REQUIRED`, two-turn review |
| Streaming + zero-wait TTS | Partial | LiveKit stream; no speculative speak-ahead |
| Self-improving prompt meta-loop | Gap | Weekly Hermes patch — not built |

### 3.2 Integration architecture

| Concept | Status | Evidence |
|---------|--------|----------|
| Thin voice wrapper over Hermes/FirstMate | **Done** | ADR in CLARITY Phase 3; `agent.py`, fleet read-only |
| Discord / crew unchanged | Mapped only | Fleet snapshot reads disk; no Discord bridge in ADVoi |
| PWA first (no APK) | **Done** | ADR-001, `web/` |
| LiveKit transport + Pipecat brain | **Done** | `Dockerfile.voice`, `VoiceSession.tsx` |
| Function calling to VPS tools | Partial | Frame run API; not open-ended tools |

### 3.3 Decision system

| Concept | Status | Evidence |
|---------|--------|----------|
| Decision Frame (voice + buttons) | **Done** | `decision/frames.py`, `VoiceSession.tsx` |
| Optionality every turn | Partial | 3 frames only; not dynamic option cards |
| Lavish rejected | **Done** | CLARITY Phase 4; desktop `/briefs/[id]` instead |
| Deep analysis deferred to desktop | **Done** | Review queue + brief pages |
| Decision Briefs | Partial | Postgres + queue; not full trade-off schema |
| DEL inside Aether, harness-triggered | Mapped only | CLARITY D-15; stub |

### 3.4 Memory & state

| Concept | Status | Evidence |
|---------|--------|----------|
| Memory loop (post-session extract) | Partial | `retain_turn`; no session-end agent |
| Hermes reflection loop (30–60 min) | Gap | Not built |
| Protocol registry | Gap | Frames hardcoded in `frames.py` |
| Voice-state sync (focus, last 3 decisions) | Partial | Redis ephemeral; no session focus API |
| Escalation ladder (Hermes vs FirstMate) | Gap | Not built |
| master-state.json unified state | Mapped only | CLARITY deferred; `postgres_store` partial |
| Priority Engine | Gap | Described in main1; not implemented |

### 3.5 Mode switching & triggers

| Concept | Status | Evidence |
|---------|--------|----------|
| "Open decision mode" / project load | Partial | Keyword intents map to 3 frames only |
| "Show my priorities" | Gap | No Priority Engine |
| Execution / research / decision modes | Gap | No mode state machine |
| Voice Command Registry | Mapped only | CLARITY §7.1 deferred |

### 3.6 Verticals & squads

| Concept | Status | Evidence |
|---------|--------|----------|
| Isolated verticals (Project, Decision, Memory, Workflow, Priority) | Mapped only | CLARITY §3.2; Decision vertical only in code |
| Aether = Squad Coordinator | Mapped only | `advoi/aether/` stub |
| Guardian / Sentinel | Mapped only | `guardian_log.py` JSONL only |
| 5-role / 3-role squads | Mapped only | CLARITY §3.5; `squads/` stub if present |
| Pathfinder, Systems Engineer, Foresight | Mapped only | Squad design only |
| 3-day silence → pause + notify | Mapped only | CLARITY D-22; not implemented |
| Staging-only squad autonomy | Mapped only | CLARITY D-07 |
| OODA loop in squads | Mapped only | Design only |

### 3.7 Data & visualization

| Concept | Status | Evidence |
|---------|--------|----------|
| Graph + Vector DB | Mapped only | CLARITY Phase 1; Postgres+Redis only live |
| React Flow dashboard | Gap | Phase 4 |
| Cross-project insights (Hermes) | Partial | Brief curator memory recall |
| Personal ERP on master-state | Mapped only | main1 + CLARITY deferred |

---

## 4. main2.txt — Executive OS, orchestration, agent ecosystem

| Concept | Status | Evidence |
|---------|--------|----------|
| Pipecat = LLM/pipeline layer | **Done** | `voice/agent.py` |
| LiveKit = transport only | **Done** | PWA + SFU staging |
| Function calling architecture (10 principles) | Mapped only | main2; partial via frame endpoints |
| Orchestrator above function calling | Partial | Intent classifier + frame_runner; not full executive layer |
| Ontology layer above orchestrator | Mapped only | CLARITY §2; no runtime ontology service |
| FirstMate + treehouse + no-mistakes | Mapped only | Fleet reads FirstMate data dir; no spawn |
| Paperclip / TheBotCompany rejected | **Done** | CLARITY Phase 3 |
| CrewAI as planner + FirstMate executor | Mapped only | Decision: stick with FirstMate |
| Letta operational memory | Partial | `letta.py` scaffold, off |
| Hermes memory / reflection | Partial | Hindsight bridge + recall at session start |
| OpenRouter model routing | **Done** | `llm/openrouter.py` |
| Local LLM (16GB) for intent | Gap | Cloud STT/LLM today |
| Kokoro + Parakeet client voice | **Done** | `/voice-local`, Path B |
| Executive + Orchestrator prompts | Mapped only | main2 end; not separate prompt files |
| ntfy / app notifications default | Gap | Voice-first only today |

---

## 5. Cross-source stack alignment

```
[ontology.txt]     Strategy Stack + harness mapping
        ↓
[main2.txt]        Ontology → Orchestrator → Function calling → VPS
        ↓
[main1.txt]        Voice harness + Decision Frames + Verticals + Aether/Guardian
        ↓
[aganticall.txt]   Quality loops on top (reflection, progressive discovery)
```

**ADVoi Build 1.5 implements the middle transport + Decision slice:**

```
PWA (voice + 3 frames) → LiveKit → Pipecat → frame_runner → Hermes memory / FirstMate fleet files
```

Everything above Decision vertical and below full Strategy Stack enforcement is **mapped, not built**.

---

## 6. Coverage score (honest)

| Source file | Mapped in CLARITY/insights | Built in Build 1.5 |
|-------------|---------------------------|-------------------|
| ontology.txt | ~95% | ~10% (principles in copy/API only) |
| aganticall.txt | ~90% | ~0% |
| main1.txt | ~90% | ~35% (voice + frames + fleet/briefs/review) |
| main2.txt | ~85% | ~40% (Pipecat/LiveKit, frames, memory bridge) |

**Nothing material from the four files is missing from documentation.** Large portions are intentionally deferred to Phase 4+ per `improvement-roadmap.md`.

---

## 7. Highest-priority gaps (if continuing after E2E sign-off)

1. **PWA analytics panel** — render `detail` from fleet frame (projects, backlog, Aether verdict)
2. **Priority Engine + master-state** — `main1.txt` unified state
3. **Mode switching** — decision / execution / priorities modes beyond 3 frames
4. **Memory loop + reflection** — post-session extract; Hermes 45m review
5. **Formal ontology enforcement** — PostgreSQL schemas + optional Open Ontologies MCP
6. **React Flow observability** — subsystems, squads, health (`CLARITY` Phase 7)
7. **Progressive discovery loops** — `aganticall.txt` for Aether/Hermes quality

---

## 8. Doc index (already exists)

| Source | Insight doc |
|--------|-------------|
| ontology.txt | `docs/insights/03-ontology-and-strategy-stack.md` |
| aganticall.txt | `docs/insights/05-agentic-progressive-discovery.md` |
| main1.txt | `docs/insights/01-voice-loops-and-harness.md` |
| main2.txt | `docs/insights/02-pipecat-livekit-executive-os.md` |
| All | `docs/CLARITY-FRAMEWORK.md` |
| Inventory | `docs/SOURCE-MATERIALS.md` |