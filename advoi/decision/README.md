# decision/

Decision intelligence — frames, briefs, and optionality analysis.

## Purpose

- **Decision frames** — structured context for high-stakes choices
- **Briefs** — concise summaries for voice delivery
- **Optionality** — track reversible vs irreversible paths

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Decision templates, scoring | Venture portfolio (→ `aether/`) |
| Option value tracking | Crew execution (→ `squads/`) |
| Voice-optimized brief formatting | Raw document parsing (→ `ingestion/`) |

## Key Artifacts

- **Frame** — `{ context, options[], constraints, recommendation, confidence }`
- **Brief** — voice-ready summary (≤ 2 sentences per section)
- **Optionality log** — timestamped decision with reversal cost