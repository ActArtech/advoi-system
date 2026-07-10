# ADVoi Decision Log

> Architecture Decision Records (ADR) for the ADVoi system.  
> Format: numbered decisions with context, options, outcome, and date.

---

## How to Use This Log

1. **Add a new decision** when a significant architectural or product choice is made
2. **Never delete** — supersede with a new decision referencing the old one
3. **Status values:** `Accepted` | `Superseded` | `Deprecated` | `Proposed`
4. Cross-reference `CLARITY-FRAMEWORK.md` for full context

### ADR Template

```markdown
## ADR-XXX: Title

**Date:** YYYY-MM-DD  
**Status:** Accepted  
**Deciders:** [who decided]

### Context
[What is the issue?]

### Options Considered
1. Option A — [description]
2. Option B — [description]
3. Option C — [description]

### Decision
[What was decided and why]

### Consequences
- Positive: [...]
- Negative: [...]
- Risks: [...]
```

---

## Decision Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-001 | Web PWA First, No APK | Accepted | 2026-07-07 |
| ADR-002 | LiveKit + Pipecat Voice Stack | Accepted | 2026-07-07 |
| ADR-003 | Keep Hermes + FirstMate Backend | Accepted | 2026-07-07 |
| ADR-004 | Voice Layer as Thin Stateless Wrapper | Accepted | 2026-07-07 |
| ADR-005 | Aether as Portfolio Manager | Accepted | 2026-07-07 |
| ADR-006 | Guardian for Security & Recovery | Accepted | 2026-07-07 |
| ADR-007 | Permanent Squads with Manual Hibernate | Accepted | 2026-07-07 |
| ADR-008 | Staging-Only Autonomy for Squads | Accepted | 2026-07-07 |
| ADR-009 | Hybrid Memory Architecture | Accepted | 2026-07-07 |
| ADR-010 | Reject Lavish for Decision Review | Accepted | 2026-07-07 |
| ADR-011 | Skip Coolify — Agentic Deploy | Accepted | 2026-07-07 |
| ADR-012 | Decision Frames with Desktop Deep Analysis | Accepted | 2026-07-07 |
| ADR-013 | PostgreSQL as Primary Warehouse | Accepted | 2026-07-07 |
| ADR-014 | React Flow for Architecture Visualization | Accepted | 2026-07-07 |
| ADR-015 | Horizontal Ingestion & Reporting Engines | Accepted | 2026-07-07 |
| ADR-016 | DEL Inside Aether, Harness-Triggered | Accepted | 2026-07-07 |
| ADR-017 | Rule-Based Model Routing with Periodic Optimization | Accepted | 2026-07-07 |
| ADR-018 | App Notifications Default, Voice for High-Value | Accepted | 2026-07-07 |
| ADR-019 | Balanced Dual Interface (Voice + App) | Accepted | 2026-07-07 |
| ADR-020 | Two Parallel Squad Experiments (5-role + 3-role) | Accepted | 2026-07-07 |
| ADR-021 | Squad Coordination — Hybrid Control | Accepted | 2026-07-07 |
| ADR-022 | Backblaze B2 for Intelligence-Layer Backup | Accepted | 2026-07-07 |
| ADR-023 | Strategy Stack Ontology as Alignment Framework | Accepted | 2026-07-07 |
| ADR-024 | Reject TheBotCompany as Orchestrator | Accepted | 2026-07-07 |
| ADR-025 | OpenRouter for Model Routing Experiments | Accepted | 2026-07-07 |
| ADR-026 | Memory Stack — Hindsight ± Letta | Accepted | 2026-07-07 |
| ADR-027 | Portfolio Event Log as control-plane event authority | Accepted | 2026-07-10 |

### Batch notes (no new ADR)

| Date | Batch | Note |
|------|-------|------|
| 2026-07-10 | wave 2 PWA/analytics/aether | **No new ADR.** PWA `POST /api/events` beacon extends ADR-027. OTEL + guardian `trace_id` implements roadmap M4.5–M4.6. fm-bridge 60s idempotency is operational hardening. UI state machine / recovery are PWA product implementation under ADR-001/002. |

---

## ADR-001: Web PWA First, No APK

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt, main2.txt)

### Context
Need mobile access for voice interaction and project dashboards. Initial discussion explored React Native APK sideloading, Kotlin native SDK, and browser-based LiveKit web client.

### Options Considered
1. **React Native APK** — Native app, better battery/background, sideload without Play Store
2. **Kotlin native Android SDK** — Best performance, deeper phone integration
3. **Web PWA** — Browser-based, instant deployment, no build pipeline for mobile

### Decision
**Web PWA first, no APK.** Start with browser-based LiveKit web client for fastest path to working voice. Defer native app until system is stable.

### Consequences
- **Positive:** Working voice in under an hour; no sideloading friction; single codebase with desktop
- **Negative:** Limited background execution; no push notifications without service worker investment
- **Risks:** iOS Safari mic permission quirks; may need native later for notification reliability

---

## ADR-002: LiveKit + Pipecat Voice Stack

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt, main2.txt)

### Context
Need real-time voice with low latency, interruptions, and tool-calling for executive workflows. LiveKit and Pipecat were evaluated individually and together. Brief debate on whether Pipecat was necessary given existing FirstMate backend.

### Options Considered
1. **LiveKit Agents only** — Built-in agent framework, simpler stack
2. **Pipecat only** — Full pipeline but needs separate transport
3. **LiveKit (transport) + Pipecat (brain)** — LiveKit carries audio; Pipecat orchestrates STT→LLM→tools→TTS
4. **Direct audio to VPS, no framework** — Minimal but reinventing pipeline plumbing

### Decision
**LiveKit + Pipecat combo.** LiveKit = "the road" (WebRTC transport). Pipecat = "the driver" (pipeline brain with tool calling). Pipecat has built-in LiveKit transport.

### Consequences
- **Positive:** Best of both — reliable transport + flexible reasoning pipeline
- **Negative:** Two dependencies to maintain
- **Risks:** Integration complexity in Stage 1; mitigated by thin wrapper pattern

---

## ADR-003: Keep Hermes + FirstMate Backend

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt, main2.txt)

### Context
Existing system runs Hermes (architect) + FirstMate (coordinator) + crew via Discord. Evaluated alternatives: CrewAI, OpenClaw, TheBotCompany, custom orchestrator replacement.

### Options Considered
1. **Keep Hermes + FirstMate unchanged** — Add thin voice wrapper
2. **Replace with CrewAI** — More structured multi-agent framework
3. **Replace with OpenClaw** — 24/7 persistent runtime
4. **Replace with TheBotCompany** — Fully autonomous agent company

### Decision
**Keep Hermes + FirstMate backend.** Voice layer forwards to FirstMate. Crew continues in Discord. No rewrite of core agent architecture.

### Consequences
- **Positive:** Preserves working investment; FirstMate's captain model and AFK mode trusted
- **Negative:** Discord remains in the loop; not pure voice-to-execution
- **Risks:** Discord as intermediary adds latency; future direct integration possible

---

## ADR-004: Voice Layer as Thin Stateless Wrapper

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Risk of business logic leaking into mobile app or voice agent, creating duplication and drift from VPS source of truth.

### Options Considered
1. **Thin stateless wrapper** — Voice handles STT/TTS/streaming only; all logic on VPS
2. **Smart mobile client** — Some logic on phone for offline/latency
3. **Fat voice agent** — Voice agent owns decision frameworks and memory

### Decision
**Thin stateless wrapper.** Voice layer: STT → forward text → receive response → TTS. All context, memory, decision frameworks on VPS.

### Consequences
- **Positive:** Single source of truth; clean separation; easier to upgrade backend
- **Negative:** Requires constant connectivity
- **Risks:** None significant for VPS-hosted executive system

---

## ADR-005: Aether as Portfolio Manager

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Squad system needed external coordinator. Initially called "Squad Coordinator." Scope expanded from task routing to portfolio management, venture architecture, and productization.

### Options Considered
1. **Option A** — Portfolio Manager + Architect (strategic, sets direction)
2. **Option B** — Coordinator / Traffic Controller only (routing, no strategy)
3. **Option C** — Super Squad Leader (deep tactical involvement)
4. **A+C Hybrid** — Portfolio Manager who can dive deep when needed

### Decision
**Aether = A+C Hybrid.** Portfolio Manager + Senior Architect. Sets strategy, maintains master backlog, can review/override squad technical decisions, drives productization and long-term optionality. Financial P&L handled by separate future agent.

### Consequences
- **Positive:** Strong strategic coherence across 30+ projects; clear authority hierarchy
- **Negative:** Aether is complex; scope must be guarded against bloat
- **Risks:** Over-centralization; mitigated by horizontal engines and squad autonomy

---

## ADR-006: Guardian for Security & Recovery

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Autonomous squads need error handling. Evaluated Aether-handled recovery, Trust-but-Verify, fully autonomous recovery, and dedicated failure agent.

### Options Considered
1. **Option A** — Aether constantly monitors, zero tolerance
2. **Option B** — Trust but verify at milestones
3. **Option C** — Fully autonomous squad self-correction
4. **Dedicated Sentinel/Guardian agent** — On-demand failure response with own memory

### Decision
**Guardian agent** (evolved from Sentinel proposal). Dormant until issue detected. Own evolving error memory. Two notifications: Issue Detected → Issue Resolved. Aether informed for context only.

### Consequences
- **Positive:** Clean separation; efficient (only active on failure); learns from past fixes
- **Negative:** Additional agent to maintain
- **Risks:** Response delay if Guardian misconfigured; mitigated by early detection notification

---

## ADR-007: Permanent Squads with Manual Hibernate

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Squad lifecycle debated: 24/7 always-on vs mission-based vs manual control. User rejected pure 24/7 and pure mission-based.

### Options Considered
1. **Option A** — Persistent always-on (24/7 improvement loops)
2. **Option B** — Mission-based (auto-hibernate on completion)
3. **Option C** — Fully manual lifecycle
4. **Hybrid A** — On by default, manual Standby/Hibernate via voice or app

### Decision
**Hybrid Persistent (Option A modified).** Squads on by default running improvement loops. User can put any squad into Standby/Hibernate at any time via voice or app. Wake instantly with new instructions. **No auto-termination.**

### Consequences
- **Positive:** Continuous improvement without constant prompting; user retains control
- **Negative:** Resource consumption when active; need clear hibernate mechanism
- **Risks:** Squads running when not needed; mitigated by 3-day silence rule

---

## ADR-008: Staging-Only Autonomy for Squads

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Squads run on lab/testing infrastructure. Need safety boundaries for autonomous code pushes and infrastructure changes.

### Options Considered
1. **Full production access** — Maximum autonomy
2. **Staging-only** — Push to staging max; production requires approval
3. **Read-only** — Squads suggest but don't push

### Decision
**Staging-only maximum.** Squads can push to staging, create infrastructure, clone repos, spawn child squads. Production deployment requires explicit user approval. High-impact actions require confirmation.

### Consequences
- **Positive:** Safe experimentation; aligns with lab server mental model
- **Negative:** Manual step for production releases
- **Risks:** Staging drift from production; mitigated by Guardian validation

---

## ADR-009: Hybrid Memory Architecture

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Memory storage debated: centralized (Aether only), hybrid, or fully distributed across squads.

### Options Considered
1. **Option 1** — Centralized: all state in Aether, squads stateless
2. **Option 2** — Hybrid: Aether strategic + squad operational detail
3. **Option 3** — Fully distributed: squads own everything, Aether has index only
4. **User choice: Both** — Aether strategic + squad operational + ephemeral execution

### Decision
**Three-layer hybrid model:**
- **Aether Memory** — Strategic: portfolio view, stage, optionality, value, master backlog, universal insights
- **Squad Operational Memory** — Persistent: execution state, lessons learned, improvement log
- **Squad Execution Memory** — Ephemeral: last 10–15 turns, cleared/summarized at milestones

### Consequences
- **Positive:** Clarity at strategic level; rich operational detail; anti-hallucination through separation
- **Negative:** Sync protocol needed between layers
- **Risks:** Inconsistency if debrief protocol not followed

---

## ADR-010: Reject Lavish for Decision Review

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
lavish-axi (Kun Chen) turns FirstMate outputs into interactive HTML review surfaces. Explored for complex decision review on mobile and desktop.

### Options Considered
1. **Integrate Lavish** — Rich HTML artifacts for complex decisions
2. **Lavish for desktop only** — Triggered when back at computer
3. **Custom Decision Frames + Briefs** — Lightweight mobile + structured desktop review
4. **10x multimodal with Lavish-style annotations** — Full interactive feedback

### Decision
**Reject Lavish.** Too token-heavy, overkill for mobile. Replace with **Decision Frames** (quick voice path) and **Decision Briefs** (deep analysis queued for desktop). Zero Lavish dependency.

### Consequences
- **Positive:** Lower token cost; cleaner mobile experience; purpose-built decision flow
- **Negative:** Lose interactive HTML annotation capability
- **Risks:** Decision Briefs must be well-designed to match Lavish's review quality

---

## ADR-011: Skip Coolify — Agentic Deploy

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (data.txt, main1.txt)

### Context
Coolify evaluated as PaaS for managing PostgreSQL, agents, Metabase, and 10+ services on VPS. User already uses agentic coding for deployment.

### Options Considered
1. **Coolify** — Web UI PaaS with MCP, auto SSL, one-click templates
2. **Direct VPS + Docker** — Manual/agentic deployment
3. **Coolify + agents** — Agents deploy through Coolify API
4. **Portainer** — Lightweight monitoring only

### Decision
**Skip Coolify.** Agentic deployment already handles lifecycle. Coolify creates competing abstraction layer. Use Docker Compose + PM2/systemd. Portainer optional for monitoring.

### Consequences
- **Positive:** No competing deploy layers; agents own full lifecycle
- **Negative:** No pretty deploy dashboard; more agent responsibility
- **Risks:** Agent deploy errors; mitigated by Guardian monitoring

---

## ADR-012: Decision Frames with Desktop Deep Analysis

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Need optionality at every major turn — voice or button triggers. Complex decisions shouldn't be forced on mobile.

### Options Considered
1. **Immediate full decision on mobile** — All options presented in rich detail
2. **Quick voice + deep desktop** — Simple options on mobile; "Prepare full decision" queues brief for desktop
3. **Desktop only for all decisions** — Mobile is status-only

### Decision
**Dual path:** Quick Voice Path (2–3 verbal options, instant choice) + Deep Analysis Path ("Prepare full decision" → Decision Brief on desktop with options, trade-offs, data, recommendations).

### Consequences
- **Positive:** Mobile stays fast; complex decisions get proper review surface
- **Negative:** Async decision flow requires state management for pending decisions
- **Risks:** Pending decisions forgotten; mitigated by app notifications and backlog integration

---

## ADR-013: PostgreSQL as Primary Warehouse

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt, data.txt, gstak tenet.txt)

### Context
Data layer needed for 30+ projects. Evaluated per-project Postgres, SurrealDB, DuckDB, ClickHouse, Nile, YugabyteDB.

### Options Considered
1. **Per-project dedicated PostgreSQL** — Perfect isolation, high overhead
2. **Single PostgreSQL, schema-per-project** — Isolation with efficiency
3. **SurrealDB** — Multi-model, graph + vector native
4. **PostgreSQL + Qdrant + Neo4j** — Specialized stores per concern

### Decision
**PostgreSQL as primary warehouse** with schema-per-project (and RLS). Qdrant/Chroma for vectors and Neo4j for graph relationships as complementary stores. Not per-project database instances.

### Consequences
- **Positive:** Mature, Metabase-compatible, efficient on single VPS
- **Negative:** Multi-store complexity (Postgres + vector + graph)
- **Risks:** Schema proliferation across 30 projects; mitigated by Aether governance

---

## ADR-014: React Flow for Architecture Visualization

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main2.txt)

### Context
Need visual representation of meta-system architecture with rules, gates, actions, and health status per component. Evaluated n8n, Sim Studio, Flowise, Excalidraw.

### Options Considered
1. **n8n / Make / Activepieces** — Trigger-based workflow canvas
2. **React Flow (custom build)** — Full control over node types and data
3. **Sim Studio / Flowise AgentFlow** — Pre-built on React Flow
4. **Static diagrams (Excalidraw/Miro)** — Manual, not interactive

### Decision
**React Flow** with custom `SystemNode` component. Each node carries: name, rules/gates, actions, health status. NodeToolbar for quick actions. Sidebar for full detail on click.

### Consequences
- **Positive:** Maximum flexibility; owns the meta-architecture representation; interactive
- **Negative:** Build effort required; not a ready-made solution
- **Risks:** Scope creep in viz features; keep focused on architecture, not general workflow automation

---

## ADR-015: Horizontal Ingestion & Reporting Engines

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Two new capabilities needed: (1) large text intake → structured action, (2) external reporting/communication with feedback import. Placement in hierarchy debated.

### Options Considered
1. **Option A** — Both managed by Aether
2. **Option B** — Independent horizontal engines parallel to Aether and Guardian
3. **Option C** — Ingestion under Aether, Reporting horizontal

### Decision
**Option B — Horizontal engines.** Ingestion Engine and Reporting & Communication Engine sit parallel to verticals. Serve any project or squad. Keeps Aether focused on portfolio/architecture.

### Consequences
- **Positive:** Clean vertical/horizontal separation; scalable; reusable across projects
- **Negative:** More components to build and monitor
- **Risks:** Unclear ownership for engine failures; mitigated by Guardian scope

---

## ADR-016: DEL Inside Aether, Harness-Triggered

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
DEL (Decision Engineering Layer) agent needed for decision framing, logging, and tracing decision flow across projects.

### Options Considered
1. **Option A** — DEL under Aether, blocks flow until framing complete
2. **Option B** — DEL parallel, independent observer
3. **Option C** — DEL built into Aether, activates on harness triggers only

### Decision
**Option C.** DEL is part of Aether. Activates as a loop through harness engineering only when specific decision triggers are met. Does not block normal execution flow.

### Consequences
- **Positive:** Decision traceability without friction; aligned with harness pattern
- **Negative:** Trigger conditions must be carefully defined
- **Risks:** Missing decisions if triggers too narrow; mitigated by periodic review

---

## ADR-017: Rule-Based Model Routing with Periodic Optimization

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Multiple model tiers needed (local, fast cloud, high-intelligence). Evaluated per-task evaluation, fixed rules, and hybrid approaches. Cost framed as optimization, not bankruptcy prevention.

### Options Considered
1. **Option A** — Aether evaluates every task for routing
2. **Option B** — Fixed rules per task type
3. **Option C** — Rules for common tasks + Aether evaluation for ambiguous
4. **Modified B** — Fixed rules + Aether optimization review every 2–3 days

### Decision
**Rule-based tiered routing** with Aether optimization review every 2–3 days. OpenRouter for testing. Value-per-Token tracking as guiding metric.

### Consequences
- **Positive:** Predictable costs; structure with adaptive improvement
- **Negative:** Initial rules may be suboptimal until first optimization cycle
- **Risks:** Misrouted tasks wasting Tier 2; mitigated by periodic review

---

## ADR-018: App Notifications Default, Voice for High-Value

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Squad reporting frequency debated: voice updates vs daily digest vs stage notifications. User has multiple projects; noise is a concern.

### Options Considered
1. **Voice for all updates** — Maximum awareness, high noise
2. **App notifications only** — Low noise, may miss critical items
3. **Hybrid** — App default, voice for high-value/critical only

### Decision
**App notifications default** (6–8 word stage updates). Voice only for high-value or critical moments. Optional daily consolidated digest.

### Consequences
- **Positive:** Low distraction; fits multi-project workflow
- **Negative:** May miss urgency without proper priority classification
- **Risks:** Under-notification for important non-critical items; mitigated by dashboard

---

## ADR-019: Balanced Dual Interface (Voice + App)

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Observability layer interface priority debated: dashboard-first, voice-first, or balanced.

### Options Considered
1. **Option A** — Dashboard-first, voice secondary
2. **Option B** — Voice-first, dashboard for deep review only
3. **Option C** — Balanced dual interface, both first-class

### Decision
**Option C — Balanced dual interface.** Voice primary for interaction (user preference). App optimized for speed, clarity, planning, backlog editing, and complex decisions. Both have advanced triggers.

### Consequences
- **Positive:** Best of both modalities; no capability gap between interfaces
- **Negative:** Must maintain feature parity across voice and app
- **Risks:** Drift between interfaces; mitigated by unified state sync

---

## ADR-020: Two Parallel Squad Experiments (5-role + 3-role)

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Squad roles refined from 5 (Black Eagles analogy) to 3 (combined roles). User clarified these are parallel experiments, not a replacement.

### Options Considered
1. **5-role only** — Full specialization
2. **3-role only** — Reduced, function-combined
3. **Both as parallel experiments** — Evaluate independently

### Decision
**Both experiments in parallel.** 5-role (Leader, Pathfinder, Systems Engineer, Foresight, Executor) and 3-role (Leader, SE+Foresight, Executor+Pathfinder). Both modular, standalone, pluggable.

### Consequences
- **Positive:** Empirical comparison; flexibility per mission type
- **Negative:** Double experiment overhead
- **Risks:** Confusion between models; mitigated by clear callsigns and Aether tracking

---

## ADR-021: Squad Coordination — Hybrid Control

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
How much autonomy squads have vs Aether oversight.

### Options Considered
1. **Option A** — Centralized: Aether assigns everything
2. **Option B** — Hybrid: autonomy within mission, approval for major changes
3. **Option C** — Decentralized: full squad autonomy, Aether informed after

### Decision
**Option B — Hybrid Control.** Squads execute and improve within assigned mission autonomously. Must get Aether approval for: new major tasks, direction changes, spawning child squads.

### Consequences
- **Positive:** Speed for execution; control for strategic shifts
- **Negative:** Approval latency for pivots
- **Risks:** Bottleneck if Aether overwhelmed; mitigated by clear approval criteria

---

## ADR-022: Backblaze B2 for Intelligence-Layer Backup

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Backup strategy debated. GitHub covers code but not Aether memory, squad operational memory, decision frameworks, or master state.

### Options Considered
1. **GitHub only** — Sufficient for code
2. **VPS local backup only** — Same failure domain as primary
3. **Backblaze B2 daily sync** — Cheap cloud backup for intelligence layer
4. **Google Drive** — Alternative cloud backup

### Decision
**Two-layer backup:** GitHub for code + **Backblaze B2** daily automated backup for intelligence layer (databases, JSON/memory files, master state). Weekly full snapshot.

### Consequences
- **Positive:** ~$6/TB/month; protects most valuable asset (learned intelligence)
- **Negative:** Another service to configure and monitor
- **Risks:** Backup corruption; mitigated by weekly snapshots and restore testing

---

## ADR-023: Strategy Stack Ontology as Alignment Framework

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (ontology.txt)

### Context
System complexity growing across 30+ repos. Need governance for naming, relationships, and architectural boundaries.

### Options Considered
1. **Ad-hoc naming and structure** — Fast, chaotic at scale
2. **Strategy Stack Ontology** — Layered alignment from Purpose to Object
3. **Full OWL ontology with Protégé** — Formal, heavy governance
4. **BFO-based ontology (agentic-redux)** — Upper ontology for agent safety

### Decision
**Strategy Stack Ontology** as alignment framework. Formal OWL tooling deferred. Event-centric modeling and named relationships adopted. Agentic harness mapped to ontology layers.

### Consequences
- **Positive:** Clear precedence rules; traceability from objects to purpose
- **Negative:** Requires discipline to maintain as living artifact
- **Risks:** Ontology drift; mitigated by versioned reviews and DEL logging

---

## ADR-024: Reject TheBotCompany as Orchestrator

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main2.txt)

### Context
TheBotCompany evaluated as alternative to FirstMate. User found it unreliable — failing to trigger, looping, hitting budget limits.

### Options Considered
1. **TheBotCompany** — Fully autonomous agent company model
2. **FirstMate** — Captain model with smart delegation and AFK mode
3. **CrewAI** — Role-based production framework

### Decision
**Reject TheBotCompany.** Keep FirstMate. Philosophy difference: FirstMate keeps user as captain; TheBotCompany removes captain and fails in practice on real tasks.

### Consequences
- **Positive:** Reliable orchestration with proven AFK mode
- **Negative:** Less autonomous than theoretical bot company model
- **Risks:** FirstMate's code-centric focus may need thin orchestrator for non-dev workflows

---

## ADR-025: OpenRouter for Model Routing Experiments

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture conversation (main1.txt)

### Context
Model routing rules need testing before production lock-in. Multiple models across tiers.

### Options Considered
1. **Direct API per provider** — Maximum control, complex config
2. **OpenRouter** — Unified multi-model routing for testing
3. **Local only** — Privacy but limited capability

### Decision
**OpenRouter for testing** phase of tiered routing. Production rules locked after optimization cycles.

### Consequences
- **Positive:** Easy A/B testing of models per task type
- **Negative:** Additional dependency and markup
- **Risks:** Provider outages; mitigated by fallback rules in routing config

---

## ADR-026: Memory Stack — Hindsight ± Letta

**Date:** 2026-07-07  
**Status:** Accepted  
**Deciders:** Architecture + Aether VPS standard  
**Supersedes:** Partial implementation detail of ADR-009 (storage backends)

### Context

ADR-009 defined three memory tiers (strategic, operational, ephemeral) but not which **engines** back each tier. Hindsight and Letta solve different problems. Running everything (Cognee, SurrealDB, etc.) creates duplicate beliefs and ops burden.

### Options Considered

1. **Hindsight only** — Hermes-native; facts, observations, mental models; benchmark-strong synthesis
2. **Letta only** — Self-editing agent memory, MemFS, persistent identity
3. **Both with strict boundaries** — Hindsight strategic + Letta operational + Postgres structured + Redis ephemeral
4. **Cognee + SurrealDB + both** — Rejected as too many stores

### Decision

**Option 3 — phased:**

- **Phase 1 (now):** Hindsight via `docker exec hermes hermes memory setup`
- **Phase 2 (v0.2):** Optional Letta at `/opt/letta` — separate compose
- **Always:** Postgres for structured canonical state; Redis for ephemeral only
- **Never:** Guardian errors → memory; fleet backlog → memory

Implementation: `advoi/memory/write_targets.py` + `MemoryRouter` with explicit `MemoryEventType` routing.

### Consequences

- **Positive:** Clear write targets; Hermes path immediate; Letta optional without rework
- **Negative:** Two systems to operate if both enabled
- **Risks:** Double-write if routing table violated — mitigated by `EVENT_WRITE_MAP` and code review

### Checklist

- [ ] Hindsight in Hermes
- [ ] `MEMORY_PROVIDER=hindsight` in deploy/.env
- [ ] Letta only when `LETTA_ENABLED=true` and `/opt/letta` up
- [ ] ADR recorded; `.aether/DECISIONS.md` synced

---

## ADR-027: Portfolio Event Log as control-plane event authority

**Date:** 2026-07-10  
**Status:** Accepted  
**Deciders:** Architecture review + AFK wave (moat R1)  
**Ship:** `advoi-data-memory-events-pel-01` (design) · `advoi-analytics-pel-schema-01` @ `7682b96`  
**Detail:** [07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md) · [migration-plan](../../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md)

### Context

Postgres already has thin `memory_events` rows written via structured retain. Moat R1 and ARCHITECTURE-DATA-MEMORY-REVIEW require a typed, append-only **Portfolio Event Log** (venture, source, type, guardian, execution, trace). Keeping dual long-term tables risks dual authority.

### Options Considered

1. **Dual tables forever** — `memory_events` + `portfolio_events`  
2. **In-place ALTER/rename** of `memory_events`  
3. **New `portfolio_events` authority + deprecate `memory_events`** *(chosen)*

### Decision

**`portfolio_events` is the single control-plane event authority.** Create new table; idempotent backfill via `legacy_memory_event_id`; cut over writers; do **not** drop `memory_events` until soak checklist complete. Emit via `advoi.analytics.pel.append_event` / `safe_append_event` from frame runs, fleet triggers (with guardian gate), and voice intents. No live Hindsight double-write (ADR-026 boundary); optional nightly synthesis later.

### Consequences

- **Positive:** Clear moat R1 primitive; typed analytics; safe dual-run window  
- **Negative:** Short dual-write/migration window; staging T2 row proof still open (M10.4)  
- **Risks:** Writers bypassing PEL — mitigate with T0 emit tests and staging T2 query gate

### Checklist

- [x] Schema + migration SQL (`deploy/migrations/001_portfolio_events.sql`)
- [x] Minimum emit points (frame / fleet / voice) + T0 tests
- [x] Design doc + migration plan
- [ ] Staging M10.4: ≥1 row after fleet/frame with `DATABASE_URL`
- [ ] Deprecate/drop `memory_events` after soak (not yet)

---

*End of decision log. Add new ADRs above this line.*