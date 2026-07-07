# Conversation Insights — Index

> Distilled markdown from raw `.txt` conversation sources in `deployment/advoi/`.  
> These inform `CLARITY-FRAMEWORK.md` and `decision-log/DECISION-LOG.md` but are easier to scan for operators and implementers.

## Source map

| Insight doc | Source `.txt` | Primary topics |
|-------------|---------------|----------------|
| [01-voice-loops-and-harness.md](01-voice-loops-and-harness.md) | `main1.txt` | Voice loops, confirmation harness, Hermes/FirstMate bridge, squads, decision frames |
| [02-pipecat-livekit-executive-os.md](02-pipecat-livekit-executive-os.md) | `main2.txt` | Pipecat vs LiveKit, function calling, orchestrator layer, ontology stack |
| [03-ontology-and-strategy-stack.md](03-ontology-and-strategy-stack.md) | `ontology.txt` | Domain ontology, events, JTBD, agentic ontology tools |
| [04-ingestion-data-bi.md](04-ingestion-data-bi.md) | `data.txt` | Ingestion pipelines, warehouse, Cube/Superset, analytics agents |
| [05-agentic-progressive-discovery.md](05-agentic-progressive-discovery.md) | `aganticall.txt` | Reflexion loops, progressive discovery, agentic critique |
| [06-ai-native-saas-principles.md](06-ai-native-saas-principles.md) | `newaistanderd.txt` | Intelligence layer, outcomes over features, speed as moat |
| [07-memory-stack-comparison.md](07-memory-stack-comparison.md) | `gstak tenet.txt` | G-Stack/GBrain, Hindsight, Letta, Mnemosyne, Nexus/Graphify critique |
| [08-venture-poker-decision-model.md](08-venture-poker-decision-model.md) | `poker.txt` | Staged bets, fold discipline, range thinking, public/private information |

Raw files live at `deployment/advoi/*.txt`. See [SOURCE-MATERIALS.md](../SOURCE-MATERIALS.md).

## How insights became architecture

| Insight theme | Locked in ADVoi as |
|---------------|-------------------|
| Thin voice wrapper | ADR-002, `advoi/voice/` |
| Web PWA over APK | ADR-001 |
| Confirmation harness | `ADVOI_CONFIRMATION_REQUIRED`, voice prompts |
| Hindsight via Hermes | ADR-026, `docs/MEMORY-STACK.md` |
| Reject Lavish / Coolify | CLARITY-FRAMEWORK §8 |
| Decision frames (Stage 2) | Disabled buttons in `VoiceSession.tsx` |
| Squad experiments | `advoi/squads/` stub, fleet bridge read-only |
| Staged venture bets | `.aether/BET.md`, poker insight doc |

## Maintenance

When a new `.txt` source is added:

1. Add row to [SOURCE-MATERIALS.md](../SOURCE-MATERIALS.md)
2. Create or extend an insight doc here
3. Add ADR if a decision changes
4. Bump [VERSIONS.md](../VERSIONS.md)