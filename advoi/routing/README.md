# routing/

Central nervous system for intent → model → token budget.

## Purpose

- **Intent classification** — route utterances to the correct vertical
- **Model routing** — fast brain vs slow brain model selection
- **Token management** — budget enforcement, context trimming

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Classifier, router, budget tracker | LLM provider SDK wrappers (thin, here) |
| Fast/slow brain split | Memory storage (→ `memory/`) |
| Fallback chains | Security policy (→ `guardian/`) |

## Fast / Slow Brain

| Tier | Latency target | Use case |
|------|----------------|----------|
| Fast | < 500ms | Acknowledgments, fillers, turn-taking |
| Slow | async | Tool calls, reasoning, crew dispatch |