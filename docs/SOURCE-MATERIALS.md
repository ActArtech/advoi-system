# Source Materials — Conversation Inputs

> Raw conversation transcripts that informed ADVoi v0.1.0 architecture and clarity framework.

## Primary Sources

| File | Location | Scope |
|------|----------|-------|
| `main1.txt` | `../main1.txt` | Voice system design, Hermes/FirstMate integration, decision frames, squads, Aether, Guardian, memory, routing, React Flow |
| `main2.txt` | `../main2.txt` | Voice-first executive OS, Pipecat/LiveKit, function calling, ontology stack, FirstMate ecosystem, agent framework comparisons |
| `ontology.txt` | `../ontology.txt` | Strategy Stack Ontology, events, JTBD, outcome-driven development, agentic harness mapping |
| `data.txt` | `../data.txt` | Ingestion pipelines, BI stack, Cognee, SigNoz, Metabase, Budibase, Coolify evaluation |
| `aganticall.txt` | `../aganticall.txt` | Agentic loops, progressive discovery, Reflexion patterns |
| `newaistanderd.txt` | `../newaistanderd.txt` | AI-Native SaaS principles (intelligence layer, outcomes, speed) |
| `gstak tenet.txt` | `../gstak tenet.txt` | GStack/GBrain, memory systems (Hindsight, Letta, Mnemosyne), Nexus/Graphify critique |
| `poker.txt` | `../poker.txt` | Range-based decision making, staged bets, venture mindset (supporting mental model) |

## Distilled insight docs

Each source has a scannable markdown summary in `docs/insights/`:

| Source | Insight doc |
|--------|-------------|
| `main1.txt` | [insights/01-voice-loops-and-harness.md](insights/01-voice-loops-and-harness.md) |
| `main2.txt` | [insights/02-pipecat-livekit-executive-os.md](insights/02-pipecat-livekit-executive-os.md) |
| `ontology.txt` | [insights/03-ontology-and-strategy-stack.md](insights/03-ontology-and-strategy-stack.md) |
| `data.txt` | [insights/04-ingestion-data-bi.md](insights/04-ingestion-data-bi.md) |
| `aganticall.txt` | [insights/05-agentic-progressive-discovery.md](insights/05-agentic-progressive-discovery.md) |
| `newaistanderd.txt` | [insights/06-ai-native-saas-principles.md](insights/06-ai-native-saas-principles.md) |
| `gstak tenet.txt` | [insights/07-memory-stack-comparison.md](insights/07-memory-stack-comparison.md) |
| `poker.txt` | [insights/08-venture-poker-decision-model.md](insights/08-venture-poker-decision-model.md) |

## How These Map to Documentation

| Output Doc | Primary Sources |
|------------|-----------------|
| `CLARITY-FRAMEWORK.md` | All sources — synthesis |
| `PLAN-SETUP-REVIEW.md` | VPS setup, portfolio guide, Stage 1 code review |
| `insights/*.md` | Per-source distillation (see table above) |
| `decision-log/DECISION-LOG.md` | main1, main2, data, ontology |
| `dev-log/DEV-LOG.md` | Scaffold + implementation notes |
| `error-log/ERROR-LOG.md` | main1 (Guardian design) |

## Versioning Rule

When new conversation resources are added:

1. Place file in `deployment/advoi/` (or `docs/sources/` once migrated)
2. Add row to this index
3. Update `CLARITY-FRAMEWORK.md` evolution timeline
4. Add ADR if a locked decision changes
5. Bump version in `docs/VERSIONS.md`