# Shaped Bet — Stage 1 Voice + PWA

## Metadata

| Field | Value |
|-------|-------|
| **Bet name** | Stage 1 Voice + PWA |
| **Status** | active |
| **Appetite** | 3 days |
| **Stage** | Build |
| **Shaped by** | founder + ADVoi agents |
| **Sprint start** | 2026-07-07 |

## Problem

Executive needs hands-free portfolio control from mobile without APK friction. Existing Hermes + fleet backends are strong but lack a thin voice entry path and installable web shell.

## In scope

- [x] Pipecat agent with LiveKit transport (OpenAI STT/LLM/TTS)
- [x] FastAPI token endpoint + health
- [x] Next.js PWA shell with mic connect
- [x] Memory recall injected into voice system prompt
- [x] Port registry row for advoi
- [x] `.aether/` bootstrap on advoi repo only

## Out of scope

- Decision Frame button actions (Stage 2)
- Letta operational memory (v0.2 optional)
- Native APK
- Rewriting Hermes or firstmate-fleet

## Success signal

| Signal | Target | Verify |
|--------|--------|--------|
| PWA loads | 200 on advoi.keyteller.com | curl / staging check |
| Token mint | POST /api/livekit/token returns JWT | curl API |
| Voice join | User hears ADVoi greeting in room | manual mic test |
| Memory | Hindsight recall in prompt when configured | logs / bridge probe |

## Solution sketch

`web` → LiveKit room → `advoi-voice` Pipecat pipeline → memory router → spoken reply. Fleet triggers stay behind `fm-bridge.sh`.