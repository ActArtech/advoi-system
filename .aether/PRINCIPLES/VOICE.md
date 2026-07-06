# ADVoi Voice Principle

Voice is a **thin, stateless wrapper**. Intelligence stays on VPS verticals.

## Must

- LiveKit carries audio; Pipecat orchestrates STT → LLM → TTS
- Recall memory before each session prompt build
- Route fleet execution via read-only `fm-bridge.sh`
- Speak in short sentences; no markdown in TTS output

## Must not

- Embed business logic in the PWA or LiveKit client
- Store beliefs in Redis or Guardian logs
- Overwrite sibling VPS projects (/opt/firstmate-fleet, /opt/hermes, /opt/aether)