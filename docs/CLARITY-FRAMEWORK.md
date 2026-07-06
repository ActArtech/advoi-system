# ADVoi System — Clarity Framework

> **Version:** v0.1.0  
> **Status:** Initial scaffold — architecture locked, implementation in progress  
> **Last updated:** 2026-07-07  
> **Purpose:** Single source of truth for vision, ontology, architecture, evolution, and open questions

---

## 1. System Vision

### 1.1 What We Are Building

**ADVoi** is a **voice-first personal executive operating system** — not a chatbot, not a dev tool, not a dashboard app. It is a continuously operating intelligence layer that:

- Accepts voice (primary) and visual UI (secondary) input from mobile and desktop
- Routes intent to the correct agent, vertical, or squad
- Executes work through existing backends (Hermes, FirstMate, crews)
- Reports back via app notifications (default) or voice (high-value only)
- Maintains strategic memory, decision traceability, and portfolio clarity across 30+ projects
- Evolves autonomously through squads, continuous improvement loops, and self-improving harnesses

### 1.2 Core Belief (AI-Native Standard)

From `newaistanderd.txt` — three principles govern all product decisions:

| Principle | Meaning |
|-----------|---------|
| **Intelligence Layer, Not UI** | Moat = proprietary data + embedded workflows + learning from usage |
| **Capabilities & Outcomes, Not Features** | Ship autonomous task completion, not feature lists |
| **Speed is Defensibility** | Ship fast, learn faster; the system must improve daily |

### 1.3 The User Experience Promise

> Talk → System understands → Confirms consequential actions → Executes → Reports → Learns → Improves

Voice stays **lean on mobile**. Complex decisions are **prepared for desktop review**. The system never forces immediate resolution of high-stakes choices on a small screen.

---

## 2. Strategy Stack Ontology Layers

Derived from `ontology.txt` — the **Strategy Stack Ontology** provides governance boundaries. Everything below must serve the layer above.

```
Purpose
  └── Motivation
        └── Appetite
              └── Capacity ← Resources
                    └── Impact
                          └── Outcome
                                └── Job-to-be-Done
                                      └── Event
                                            └── Solution (products/features)
                                                  └── Object/Entity ← Assets
```

### 2.1 Layer Definitions

| Layer | Role in ADVoi |
|-------|---------------|
| **Purpose** | Why the platform exists — personal executive OS for portfolio + venture building |
| **Motivation** | Current strategic drivers (which initiatives matter now) |
| **Appetite** | Risk/reward tolerance per initiative |
| **Capacity** | VPS resources, token budgets, squad bandwidth, model tiers |
| **Impact** | Sustained business/user change across portfolio |
| **Outcome** | Measurable results (KPIs tied to ontology) |
| **Job-to-be-Done** | User progress goals ("get food delivered", "ship voice memory system") |
| **Event** | First-class connectors — OrderPlacementEvent, not static FK relationships |
| **Solution** | ADVoi capabilities: voice layer, squads, dashboards, ingestion |
| **Object/Entity** | Projects, squads, decisions, backlogs, memory artifacts |

### 2.2 Agentic Harness Mapping

| Stack Layer | Harness Component |
|-------------|-------------------|
| Motivation, Appetite, Capacity | Guardrails, policies, resource limits |
| Impact, Outcome, JTBD | Goal definition, loop termination criteria |
| Events, Objects | Memory layer, tool read/write targets |
| Full ontology | Shared language the harness enforces |

### 2.3 Relationship Model

- **Multiple named relationships** between any two entities (not one vague link)
- **Events as first-class citizens** for audit trails and temporal semantics
- **Reification** when relationships themselves carry properties (who approved, when, status)

---

## 3. Architecture Layers

### 3.1 Layer Model Overview

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                               │
│  Web PWA (mobile-first) │ Desktop (deep decisions)        │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  VOICE LAYER (thin, stateless)                              │
│  LiveKit transport │ Pipecat pipeline (STT→LLM→TTS→tools)  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  INTENT & ROUTING LAYER (horizontal)                      │
│  Local LLM: trigger words, mode switching, intent classify  │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐  ┌──────────▼─────────┐  ┌──────▼───────┐
│  VERTICALS   │  │  HORIZONTALS       │  │  ORCHESTR.   │
│              │  │                    │  │              │
│  Aether      │  │  Ingestion Engine  │  │  Hermes      │
│  Guardian    │  │  Reporting Engine  │  │  FirstMate   │
│  Squads      │  │  Intent/Routing    │  │  + Crew      │
│  DEL (in     │  │  DEL triggers      │  │              │
│   Aether)    │  │                    │  │              │
└───────┬──────┘  └──────────┬─────────┘  └──────┬───────┘
        │                    │                    │
┌───────▼────────────────────▼────────────────────▼───────────┐
│  DATA LAYER                                                 │
│  PostgreSQL (primary warehouse) │ Qdrant/Chroma │ Neo4j    │
│  Backblaze B2 (state backup) │ GitHub (code backup)       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Verticals (Bounded Contexts)

| Vertical | Agent/Component | Responsibility |
|----------|-----------------|----------------|
| **Portfolio & Architecture** | **Aether** | Portfolio manager, venture architect, master backlog, architectural standards, cross-project insights, DEL decision framing (triggered) |
| **Security & Recovery** | **Guardian** | Error detection, failure recovery, security, quality control — dormant until issue detected |
| **Execution** | **Squads** | Autonomous mission execution with 5-role or 3-role experiments |
| **Project** | Project Vertical | Hierarchy: Sessions → Projects → Hierarchies; auto-sorting, tagging, prioritization |
| **Decision** | Decision Vertical | Decision Frames, Decision Briefs, optionality (voice + buttons) |
| **Memory & Knowledge** | Memory Vertical | Hybrid memory: Aether strategic + Squad operational + ephemeral execution |
| **Workflow** | Workflow Vertical | Repeated-activity capture, refinement protocol, versioned workflows |
| **Priority & Execution** | Priority Vertical | Priority Engine, Value-per-Token tracking, backlog scoring |

### 3.3 Horizontals (Cross-Cutting Services)

| Horizontal | Responsibility |
|------------|----------------|
| **Ingestion Engine** | Large text/document intake → analyze → structure → route to projects/squads |
| **Reporting & Communication Engine** | External briefings, stakeholder updates, feedback import |
| **Intent & Routing Layer** | Local LLM trigger detection, mode switching, vertical routing |
| **Voice Layer** | LiveKit + Pipecat — transport + brain pipeline |
| **Observability** | Project dashboards, squad status, architecture health (React Flow viz) |

### 3.4 Orchestration (Existing Backend — Unchanged)

| Component | Role |
|-----------|------|
| **Hermes** | Deep reasoning, architecture, reflection loops, prompt self-improvement |
| **FirstMate** | Captain/coordinator — crew spawning, Discord integration, AFK mode |
| **Crew** | Specialized execution agents (dev work via treehouse + no-mistakes) |
| **Py layer** | Execution engine connecting to VPS data, structures, tools |

**Critical rule:** Voice layer is a **thin, stateless wrapper**. No business logic in mobile or LiveKit agent. All context, memory, and decision frameworks stay on VPS.

### 3.5 Squad Architecture

Two parallel experiments:

**Experiment 1 — 5-Role Squad:**
- Squad Leader (Director)
- Pathfinder
- Systems Engineer
- Foresight
- Executor

**Experiment 2 — 3-Role Squad:**
- Squad Leader (Orchestrator)
- Systems Engineer + Foresight (combined)
- Executor + Pathfinder (combined)

**Squad rules (locked):**
- Dynamic callsigns — user names each squad at spawn time
- Permanent squads — no auto-termination
- Can work across multiple projects
- Max autonomy: push to **staging only** — never production without explicit approval
- Can spawn child squads and isolated infrastructure (with Aether approval for major changes)
- OODA loop internally: Observe → Orient → Decide → Act
- Hybrid Persistent lifecycle: on by default, manual Standby/Hibernate via voice or app
- 3-day silence rule: pause development + send notification

### 3.6 Aether — Portfolio Manager

**Primary directive:** Maximize long-term optionality + architectural clarity + productization + profitability.

**Responsibilities:**
- Strategic direction and priorities across all projects
- Master backlog per project (editable by Aether, user, and squads)
- Architectural standards and health scoring
- Cross-project universal insights layer
- Squad coordination (Hybrid Control — Option B)
- Continuous Improvement Loop (internal decision framework + Priority Engine)
- DEL integration — decision framing/logging activates via harness triggers only
- Periodic model routing optimization (every 2–3 days)

**Separate (future):** Financial agent for P&L, funding, financial modeling.

### 3.7 Guardian — Security & Recovery

Evolved from "Sentinel" proposal. Renamed and locked.

- Dormant until failure/drift/quality issue detected
- Own evolving memory of errors, root causes, fixes
- Two-phase notification: **Issue Detected** → **Issue Resolved**
- Aether informed for context only (not required to act)
- Escalates to Aether only for strategic/complex issues

---

## 4. Evolution Timeline

### Phase 0 — Ontology & Data Foundations
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Strategy Stack Ontology (Purpose → Object), event-centric modeling, JTBD, outcome-driven development |
| **Explored** | Protégé, ROBOT, ODK, Open Ontologies, MCP-native ontology tools |
| **Refined** | Agentic harness + loops mapped to ontology layers; ontology as governance artifact not static diagram |
| **Final** | Strategy Stack adopted as strategic alignment framework; implementation via PostgreSQL schemas + graph relationships |

### Phase 1 — Data & Analytics Stack Exploration
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Full stack: Unstructured + Data Prepper → PostgreSQL → Cognee → SigNoz → Metabase → Budibase → ntfy |
| **Explored** | Data-Juicer, CocoIndex, Cube, Superset, SurrealDB, ERPNext, Twenty CRM, Postiz, Dub, CrowdSec |
| **Rejected** | Alpsmith (not found), Budinc (not found), per-project dedicated Postgres instances (resource waste) |
| **Refined** | Schema-per-project in single PostgreSQL; Metabase for BI; Appsmith/Budibase for internal tools |
| **Final** | **PostgreSQL primary warehouse** with schema-per-project + RLS; optional Qdrant/Chroma + Neo4j for memory graph |

### Phase 2 — Voice & Mobile Access
| Stage | What Happened |
|-------|---------------|
| **Proposed** | React Native APK sideloading, Kotlin native, browser web client |
| **Explored** | LiveKit Agents, Pipecat, Bolna, ElevenLabs TTS, Deepgram/AssemblyAI STT |
| **Rejected** | Voice-only notifications (too noisy); Lavish for mobile decision review |
| **Refined** | LiveKit = transport ("phone line"), Pipecat = brain ("driver + car") |
| **Final** | **Web PWA first, no APK**; voice-primary, dashboard for clarity; Pipecat + LiveKit combo |

### Phase 3 — Backend Integration
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Rewrite agents for voice; Discord elimination |
| **Explored** | CrewAI, OpenClaw, TheBotCompany, Paperclip, Hermes |
| **Rejected** | TheBotCompany (unreliable, no captain model); Bot Company (too noisy); full Discord removal |
| **Refined** | Thin voice wrapper → FirstMate via webhook/bot; Hermes for deep thinking |
| **Final** | **Hermes + FirstMate backend kept**; voice as thin stateless wrapper; Discord remains crew channel |

### Phase 4 — Decision & Memory Systems
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Lavish-axi interactive HTML artifacts for complex decisions |
| **Explored** | Multimodal decision cards, visual + voice optionality, 10x UX with Lavish-style annotations |
| **Rejected** | **Lavish** — overkill, token-heavy, local-browser friction on mobile |
| **Refined** | Decision Frames with dual path: Quick Voice (2–3 options) + Deep Analysis (queued for desktop) |
| **Final** | **Decision Briefs** prepared async for desktop; DEL agent inside Aether, harness-triggered only |

### Phase 5 — Squad & Portfolio Architecture
| Stage | What Happened |
|-------|---------------|
| **Proposed** | 5-role Black Eagles squad (Pathfinder, Systems Engineer, Foresight, Executor, Leader) |
| **Explored** | Red Alert analogy, OODA loops, military callsigns (Vanguard, Specter, Forge) |
| **Refined** | 3-role reduction experiment; external Squad Coordinator proposed |
| **Final** | **Aether** = external portfolio coordinator; **two squad experiments** in parallel; squads permanent |

### Phase 6 — Infrastructure & Deployment
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Coolify PaaS for one-click deploy of full stack |
| **Explored** | Coolify MCP, Portainer as lighter alternative |
| **Rejected** | **Coolify** — competes with agentic deployment layer; adds abstraction noise |
| **Refined** | Agent-owned deployment lifecycle; Portainer for monitoring only |
| **Final** | **Agentic deploy** — agents own code→deploy→monitor; Docker Compose + PM2/systemd on VPS |

### Phase 7 — Architecture Visualization
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Excalidraw, Whimsical, Miro for architecture diagrams |
| **Explored** | n8n, Sim Studio, Flowise AgentFlow |
| **Rejected** | n8n as primary viz (too trigger/automation opinionated) |
| **Final** | **React Flow** — custom SystemNode components with rules, gates, actions, health status |

### Phase 8 — Horizontal Engines
| Stage | What Happened |
|-------|---------------|
| **Proposed** | Aether owns ingestion and reporting |
| **Explored** | Option A (Aether-owned), Option B (horizontal), Option C (split) |
| **Final** | **Ingestion + Reporting as independent horizontal engines** parallel to Aether and Guardian |

---

## 5. Locked Final Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D-01 | Web PWA first, no APK | Fastest path to working voice; no Play Store friction; iterate before native |
| D-02 | LiveKit (transport) + Pipecat (brain) | Complementary: LiveKit = WebRTC audio; Pipecat = STT→LLM→tools→TTS pipeline |
| D-03 | Hermes + FirstMate backend unchanged | Existing investment; voice is thin wrapper only |
| D-04 | Aether = Portfolio Manager + Venture Architect | Owns initiatives, architecture clarity, productization, master backlog |
| D-05 | Guardian = Security, errors, fixes | On-demand activation; evolving error memory; two-phase notifications |
| D-06 | Squads permanent, no auto-termination | Long-running improvement; manual Standby/Hibernate only |
| D-07 | Staging-only max for squad autonomy | Safety boundary; production requires explicit user approval |
| D-08 | Hybrid memory model | Aether strategic + Squad operational (persistent) + ephemeral execution |
| D-09 | Lavish rejected | Token-heavy, overkill; Decision Briefs replace for desktop deep analysis |
| D-10 | Coolify skipped | Agentic deployment owns lifecycle; Coolify = competing abstraction |
| D-11 | Decision Frames: quick voice + deep desktop | Mobile stays lean; complex decisions queued as Decision Briefs |
| D-12 | PostgreSQL primary warehouse | Schema-per-project; mature BI support; single VPS efficiency |
| D-13 | React Flow for architecture viz | Custom SystemNode with rules/gates/actions; owns meta-system representation |
| D-14 | Ingestion + Reporting as horizontals | Clean vertical/horizontal separation; serves whole system not one agent |
| D-15 | DEL inside Aether, harness-triggered | Decision framing only when triggers met; no blocking flow |
| D-16 | Rule-based model routing + 2–3 day optimization | Tier 0 local → Tier 1 fast cloud → Tier 2 Hermes/high-intelligence |
| D-17 | App notifications default; voice for high-value only | Low-noise communication; daily digest optional |
| D-18 | Balanced dual interface (voice + app) | Voice primary for interaction; app for speed, clarity, planning |
| D-19 | OpenRouter for model routing testing | Easy multi-model experimentation before production routing rules |
| D-20 | Backblaze B2 for intelligence-layer backup | GitHub backs code only; Aether/squad memory needs separate backup |
| D-21 | Two squad experiments (5-role + 3-role) | Parallel evaluation; not a reduction — both modular and standalone |
| D-22 | 3-day silence → pause + notify | Prevents runaway autonomous work when user disengaged |
| D-23 | Workflow Refinement Protocol | Repeated activities become versioned, improvable workflow templates |
| D-24 | Streaming + speculative generation | Zero-wait voice: stream TTS early, pre-acknowledge, speculative tool calls |

---

## 6. Version History

| Version | Date | Changes |
|---------|------|---------|
| **v0.1.0** | 2026-07-07 | Initial scaffold: docs structure, clarity framework, decision log, dev log, error log templates; architecture decisions captured from conversation evolution |

---

## 7. Open Questions / Deferred Items

### 7.1 High Priority (Design Later)

| Item | Status | Notes |
|------|--------|-------|
| Continuous Improvement Loop detail | Deferred | Aether engine defined conceptually; needs harness integration spec |
| Squad Operational Memory schema | Deferred | Structure agreed; exact format TBD |
| master-state.json / per-project `.ether` schema | Deferred | Hybrid model locked; JSON schema not finalized |
| Model routing rules (Tier 0/1/2) | Deferred | Rule-based approach locked; exact task→tier mapping TBD |
| Value-per-Token evaluation framework | Deferred | Principle locked; metrics TBD |
| DEL harness trigger conditions | Deferred | Agent role locked; trigger list TBD |
| Voice Command Registry | Deferred | Workflow Refinement Protocol defined; registry not built |
| Project Dashboard UI spec | Deferred | Requirements captured; visual design TBD |
| Security & Access Control | Open | RBAC, auth model for PWA + VPS not defined |
| Squad-to-squad communication protocol | Open | Cross-squad coordination rules partial |
| Financial agent (P&L layer) | Future | Separate from Aether; name and scope TBD |

### 7.2 Medium Priority

| Item | Notes |
|------|-------|
| Local LLM selection for Tier 0 | Llama 3.3 / Qwen2.5 discussed; 16GB VPS constraints |
| STT/TTS final vendor lock | ElevenLabs + Deepgram leading; Kokoro for lightweight TTS |
| Memory provider for Hermes | Hindsight, Mnemosyne, Letta compared in gstak tenet.txt — not locked for ADVoi |
| Neo4j vs pg_graph | Graph store choice deferred |
| Qdrant vs Chroma | Vector store choice deferred |
| Printing Press integration | CLI tooling layer explored in main2.txt — fit TBD |
| Cortex / Repowise for 30-repo maturity | Portfolio observability tooling evaluated, not integrated |

### 7.3 Low Priority / Nice-to-Have

| Item | Notes |
|------|-------|
| Squad performance analytics | Which squads are effective |
| Squad onboarding process | Standardized spawn protocol |
| Cloudflare + Backblaze for image CDN | Side discussion; not core |
| Done-For-You business model tiers | Monetization explored; not system architecture |
| G-Stack / G-Brain integration | Evaluated; senior dev skepticism noted |

---

## 8. Tool & Repository Evaluation Matrix

### 8.1 Voice & Real-Time

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **LiveKit** | Audio transport, WebRTC, mobile connectivity | ✅ **Adopt** — transport layer |
| **Pipecat** | Voice pipeline, STT→LLM→TTS, tool calling | ✅ **Adopt** — brain layer |
| **Bolna** | Alternative voice framework | ⏸️ Skip — Pipecat stronger community/flexibility |
| **LiveKit Agents alone** | Full voice solution | ⏸️ Partial — transport only without Pipecat brain |
| **ElevenLabs** | TTS quality | ✅ **Adopt** — primary TTS candidate |
| **Deepgram / AssemblyAI** | STT streaming | ✅ **Adopt** — primary STT candidates |
| **Kokoro** | Lightweight local TTS | 🔍 Evaluate — 16GB VPS fallback |

### 8.2 Orchestration & Agents

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **Hermes** | Deep reasoning, memory, voice, self-improvement | ✅ **Keep** — architect layer |
| **FirstMate** | Captain, crew spawning, AFK mode | ✅ **Keep** — coordinator |
| **treehouse** | Git worktree isolation for crew | ✅ **Keep** — FirstMate companion |
| **no-mistakes** | Safe PR pipeline, validation | ✅ **Keep** — FirstMate companion |
| **CrewAI** | Multi-agent framework | ⏸️ Skip — FirstMate preferred |
| **OpenClaw** | 24/7 agent runtime | ⏸️ Skip — existing stack sufficient |
| **TheBotCompany** | Autonomous agent company | ❌ **Reject** — unreliable, no captain |
| **Paperclip** | Agent org chart governance | 🔍 Reference — Hermes ecosystem |
| **Routa** | Kanban agent orchestration | ⏸️ Skip — dev-delivery focused |
| **Lindy AI** | Action-driven voice platform | ⏸️ Skip — not customizable enough |

### 8.3 Memory & Knowledge

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **PostgreSQL** | Primary warehouse, transactional data | ✅ **Adopt** — primary store |
| **Qdrant / Chroma** | Vector semantic search | 🔍 Evaluate — pick one |
| **Neo4j** | Graph relationships | 🔍 Evaluate — or pg_graph |
| **Cognee** | Knowledge graph memory | ⏸️ Defer — may overlap with custom hybrid model |
| **Hindsight** | Hermes memory provider | 🔍 Evaluate — synthesis-heavy |
| **Mnemosyne** | Local tiered memory | 🔍 Evaluate — speed/privacy |
| **Letta (Leda)** | Self-editing agent memory | 🔍 Evaluate — identity/long-running |
| **G-Brain** | Git-backed markdown brain | ⏸️ Defer — ops overhead concerns |
| **Graphify** | Codebase knowledge graph | ⏸️ Existing setup — noisy; Kumiho as complement |
| **Nexus** | Decision graph | ❌ **Reject** — cluttered |
| **Memora / Kumiho / EverOS** | Advanced memory | 🔍 Evaluate — Kumiho for workflow views |

### 8.4 Data Pipeline & Analytics

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **Unstructured** | Document parsing/chunking | 🔍 Reference — ingestion layer input |
| **Data Prepper** | Modular YAML pipelines | 🔍 Reference — routing pattern |
| **Data-Juicer** | LLM data curation | ⏸️ Skip — training-focused not ingestion |
| **Metabase** | BI dashboards | 🔍 Evaluate — business analytics |
| **Cube.js** | Semantic metrics layer | 🔍 Evaluate — governed KPIs |
| **Superset** | Full BI platform | ⏸️ Skip — heavier than needed now |
| **SigNoz** | Observability/APM | 🔍 Evaluate — agent monitoring |

### 8.5 Review & Decision UI

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **Lavish (lavish-axi)** | Interactive HTML review | ❌ **Reject** — token-heavy, mobile friction |
| **Decision Frames + Briefs** | Custom decision system | ✅ **Adopt** — designed in-house |
| **React Flow** | Architecture visualization | ✅ **Adopt** — SystemNode custom components |
| **n8n** | Workflow automation canvas | ❌ **Reject** — wrong abstraction for meta-architecture |
| **Sim Studio / Flowise** | React Flow-based builders | ⏸️ Reference — build custom on React Flow |

### 8.6 Infrastructure & Deployment

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **Coolify** | PaaS deploy dashboard | ❌ **Reject** — conflicts with agentic deploy |
| **Portainer** | Lightweight container monitoring | 🔍 Evaluate — monitoring only |
| **Docker Compose + PM2** | VPS service management | ✅ **Adopt** — base infrastructure |
| **Backblaze B2** | Intelligence-layer backup | ✅ **Adopt** — state backup |
| **GitHub** | Code backup + repos | ✅ **Keep** — per-project repos |
| **OpenRouter** | Multi-model routing testing | ✅ **Adopt** — routing experiments |
| **CrowdSec** | VPS security | 🔍 Evaluate — infrastructure protection |

### 8.7 Ontology & Agentic Patterns

| Tool | Considered For | Verdict |
|------|----------------|---------|
| **Open Ontologies** | MCP-native ontology | 🔍 Reference — agent grounding |
| **Protégé + ROBOT + ODK** | Formal ontology governance | 🔍 Reference — long-term governance |
| **all-agentic-architectures** | Reflexion, self-critique loops | 🔍 Reference — harness patterns |
| **agentic-redux** | Ontology-first agent design | 🔍 Reference — safety/auditability |

---

## 9. Key Protocols (Summary)

### 9.1 Voice Prompt Structure (6-Section Template)
1. Identity & Personality
2. Response Guidelines (max 1–2 sentences, one question at a time)
3. Guardrails (confirmation for consequential actions)
4. Context (runtime-injected state)
5. Workflow (step-by-step playbooks)
6. Examples (few-shot ideal exchanges)

### 9.2 Memory Management Protocol
- **Aether layer:** Strategic state, master backlog, architectural health, universal insights
- **Squad layer:** Mission objectives, technical state, lessons learned, operational backlog slice
- **Ephemeral layer:** Last 10–15 turns; summarized to operational memory at milestones
- Squads debrief outcomes to Aether after major tasks

### 9.3 Notification Protocol
- **Default:** Simple app notification (6–8 words, stage update)
- **Voice:** Only high-value or critical moments
- **Daily digest:** One consolidated summary (optional, user-chosen time)
- **Guardian:** Issue Detected → Issue Resolved (always app; voice if critical)

### 9.4 Model Routing Tiers
| Tier | Model Class | Use Cases |
|------|-------------|-----------|
| **Tier 0** | Local LLM | Triggers, routing, status, simple coordination (~70–75%) |
| **Tier 1** | Fast cloud | Squad execution, coding, documentation, standard workflows |
| **Tier 2** | High-intelligence (Hermes) | Architecture, strategic analysis, major decision frameworks |

Optimization review every 2–3 days by Aether.

---

## 10. Related Documents

| Document | Path |
|----------|------|
| Decision Log (ADR) | `docs/decision-log/DECISION-LOG.md` |
| Development Log | `docs/dev-log/DEV-LOG.md` |
| Error Log (Guardian) | `docs/error-log/ERROR-LOG.md` |

---

## 11. Source Conversations

| File | Coverage |
|------|----------|
| `main1.txt` | Voice system, squads, Aether, Guardian, memory, decisions, architecture lock-in |
| `main2.txt` | Pipecat/LiveKit, FirstMate ecosystem, React Flow, PWA, monetization, meta-architecture |
| `ontology.txt` | Strategy Stack, events, JTBD, agentic harness mapping |
| `data.txt` | Ingestion pipelines, warehouse, BI stack, Coolify rejection |
| `aganticall.txt` | Progressive discovery, agentic loops, self-critique patterns |
| `newaistanderd.txt` | AI-Native SaaS principles |
| `gstak tenet.txt` | G-Stack/G-Brain, memory system comparison (Hindsight, Mnemosyne, Letta) |

---

*This document is a living artifact. Update on every architectural decision. Version bump on structural changes.*