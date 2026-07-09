"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./VoiceLoop.module.css";
import { useVoiceSTT } from "./VoiceSTT";
import { useVoiceTTS } from "./VoiceTTS";
import { useServerTTS } from "./useServerTTS";
import { isConfirmPhrase, mirrorPhrases, stripEmDash } from "./warmth";
import { backendLabel, isWindows, type ModelBackend } from "./modelBackend";
import {
  clearModelCaches,
  formatModelLoadError,
  probeBrowserStorage,
  storageProbeMessage,
} from "./storageProbe";
import { WARM_VOICES, type VoiceId } from "./types";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

type LoopState = "idle" | "loading" | "ready" | "listening" | "thinking" | "speaking" | "error";
export type VoiceLoopMode = "auto" | "client" | "server";
type ActiveVoiceMode = "client" | "server";

type VoiceIntentResponse = {
  action?: string;
  frame_id?: string;
  confirmed?: boolean | null;
  preview?: {
    spoken_summary?: string;
    status?: string;
    agent_id?: string;
    agent_name?: string;
  };
};

type VoiceRespondPayload = {
  spoken?: string;
  agent_id?: string;
  agent_name?: string;
  frame_id?: string;
  agents_used?: string[];
  systems?: string[];
};

type AgentRow = {
  id: string;
  name: string;
  role?: string;
  cached?: boolean;
  frame_id?: string;
};

function isFrameIntent(data: VoiceIntentResponse): data is VoiceIntentResponse & { frame_id: string } {
  const frameId = data.frame_id?.trim();
  if (!frameId) return false;
  return data.action === "frame";
}

export function VoiceLoop({ defaultMode = "auto" }: { defaultMode?: VoiceLoopMode }) {
  const [state, setState] = useState<LoopState>("loading");
  const [voiceMode, setVoiceMode] = useState<ActiveVoiceMode>(
    defaultMode === "server" ? "server" : "client",
  );
  const [status, setStatus] = useState(
    defaultMode === "server"
      ? "Checking server voice..."
      : "Loading Kokoro and Parakeet models...",
  );
  const [sttBackend, setSttBackend] = useState<ModelBackend | null>(null);
  const [ttsBackend, setTtsBackend] = useState<ModelBackend | null>(null);
  const [browserTts, setBrowserTts] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [typedLine, setTypedLine] = useState("");
  const [micLevel, setMicLevel] = useState(0);
  const [voice, setVoice] = useState<VoiceId>("af_heart");
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [activeSystems, setActiveSystems] = useState<string[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [storageHint, setStorageHint] = useState<string | null>(null);
  const [clearingCache, setClearingCache] = useState(false);
  const busy = useRef(false);
  const pendingFrame = useRef<string | null>(null);
  const initDone = useRef(false);

  const onError = useCallback((msg: string) => {
    setState("error");
    setStatus(msg);
  }, []);

  const allowAutoFallback = defaultMode === "auto";

  const clientTts = useVoiceTTS({
    voice,
    speed: 1.2,
    onError,
    onBackendReady: setTtsBackend,
    onFallback: () => setBrowserTts(true),
    reportPreloadErrors: !allowAutoFallback,
  });

  const serverTts = useServerTTS({
    onError,
    onReady: () => {
      if (voiceMode === "server") {
        setState("ready");
        setStatus("Ready (server TTS). Tap listen and speak.");
      }
    },
  });

  const speak =
    voiceMode === "server"
      ? serverTts.speak
      : clientTts.speak;
  const isSpeaking = voiceMode === "server" ? serverTts.isSpeaking : clientTts.isSpeaking;
  const usingBrowserVoice = voiceMode === "server" ? false : clientTts.usingBrowserVoice;

  const respond = useCallback(
    async (text: string) => {
      if (!text.trim() || busy.current) return;
      busy.current = true;
      setState("thinking");
      setStatus("Thinking...");
      const phrases = mirrorPhrases(text);
      try {
        let spoken = "";
        let agentLabel: string | null = null;
        let systems: string[] = [];

        if (pendingFrame.current && isConfirmPhrase(text)) {
          const frameId = pendingFrame.current;
          const frameResp = await fetch(`${apiBase}/frames/${frameId}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ confirmed: true }),
          });
          pendingFrame.current = null;
          if (frameResp.ok) {
            const frameData = await frameResp.json();
            spoken = stripEmDash(String(frameData.spoken_summary || ""));
            agentLabel = String(frameData.agent_name || frameData.agent_id || "");
            systems = Array.isArray(frameData.systems) ? frameData.systems : [];
          }
        }

        if (!spoken) {
          try {
            const intentResp = await fetch(`${apiBase}/voice/intent`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ transcript: text, preview: true }),
            });
            if (intentResp.ok) {
              const intentData = (await intentResp.json()) as VoiceIntentResponse;
              if (isFrameIntent(intentData)) {
                const previewSpoken = intentData.preview?.spoken_summary;
                if (previewSpoken) {
                  spoken = stripEmDash(String(previewSpoken));
                  agentLabel = String(
                    intentData.preview?.agent_name || intentData.preview?.agent_id || "",
                  );
                  if (
                    intentData.preview?.status === "confirmation_required" ||
                    (intentData.frame_id === "queue_deep_review" && !intentData.confirmed)
                  ) {
                    pendingFrame.current = intentData.frame_id;
                  }
                } else {
                  const refresh =
                    intentData.frame_id === "fleet_status" ||
                    intentData.frame_id === "systems_pulse";
                  const frameResp = await fetch(
                    `${apiBase}/frames/${intentData.frame_id}/run${refresh ? "?refresh=true" : ""}`,
                    {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        confirmed: Boolean(intentData.confirmed),
                        refresh,
                      }),
                    },
                  );
                  if (frameResp.ok) {
                    const frameData = await frameResp.json();
                    spoken = stripEmDash(String(frameData.spoken_summary || ""));
                    agentLabel = String(frameData.agent_name || frameData.agent_id || "");
                    systems = Array.isArray(frameData.systems) ? frameData.systems : [];
                  }
                }
              }
            }
          } catch {
            /* intent endpoint optional; fall through to warm reply */
          }
        }

        if (!spoken) {
          const resp = await fetch(`${apiBase}/voice/respond`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transcript: text, recent_phrases: phrases }),
          });
          if (resp.ok) {
            const data = (await resp.json()) as VoiceRespondPayload;
            spoken = stripEmDash(String(data.spoken || ""));
            agentLabel = String(data.agent_name || data.agent_id || "");
            systems = Array.isArray(data.systems) ? data.systems : [];
          } else {
            spoken = `I heard: ${text}. Connect the API for agent replies.`;
          }
        }

        setActiveAgent(agentLabel || null);
        setActiveSystems(systems);
        setStatus(spoken);
        setState("speaking");
        await speak(spoken);
        setState("ready");
        setStatus("Ready. Tap listen to continue.");
      } catch (e) {
        onError(e instanceof Error ? e.message : "Loop failed");
      } finally {
        busy.current = false;
      }
    },
    [onError, speak],
  );

  const onTranscript = useCallback(
    (text: string, isFinal: boolean) => {
      setTranscript(text);
      if (isFinal) void respond(text);
    },
    [respond],
  );

  const preferBrowserStt = voiceMode === "server";

  const { isListening, toggleListening, sttMode } = useVoiceSTT({
    onTranscript,
    onError,
    onBackendReady: setSttBackend,
    onMicLevel: setMicLevel,
    preferBrowser: preferBrowserStt,
  });

  const submitTypedLine = useCallback(() => {
    const line = typedLine.trim();
    if (!line) return;
    setTypedLine("");
    setTranscript(line);
    void respond(line);
  }, [respond, typedLine]);

  useEffect(() => {
    void fetch(`${apiBase}/agents`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.agents)) {
          setAgents(data.agents as AgentRow[]);
        }
      })
      .catch(() => {
        /* optional roster */
      });
  }, []);

  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;

    const switchToServerVoice = async (reason: string) => {
      setVoiceMode("server");
      setStorageHint(reason);
      setStatus(`${reason} Loading server voice...`);
      await serverTts.preload();
      setState("ready");
      setStatus("Ready (server TTS). Tap listen and speak.");
    };

    const boot = async () => {
      if (defaultMode === "server") {
        await serverTts.preload();
        setState("ready");
        return;
      }

      const storage = await probeBrowserStorage();
      if (!storage.ok) {
        await switchToServerVoice(storageProbeMessage(storage));
        return;
      }

      try {
        await clientTts.preload();
        setState("ready");
        const accel = ttsBackend ? backendLabel(ttsBackend) : "WASM";
        setStatus(`Ready (Kokoro ${accel}). Tap listen and speak.`);
      } catch (e) {
        if (allowAutoFallback) {
          await switchToServerVoice(formatModelLoadError(e));
        } else {
          onError(formatModelLoadError(e));
        }
      }
    };

    void boot();
  }, [allowAutoFallback, clientTts, defaultMode, onError, serverTts, ttsBackend]);

  const handleClearModelCache = useCallback(async () => {
    setClearingCache(true);
    try {
      const cleared = await clearModelCaches();
      setStorageHint(
        cleared.length
          ? `Cleared ${cleared.length} model cache entries. Reload the page to retry client voice.`
          : "No model caches found. Free disk space, then reload.",
      );
      setState("ready");
      setStatus("Cache cleared. Reload the page, or continue with server voice.");
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not clear model cache");
    } finally {
      setClearingCache(false);
    }
  }, [onError]);

  useEffect(() => {
    if (isListening) setState("listening");
    else if (isSpeaking) setState("speaking");
    else if (!busy.current && state !== "error") setState("ready");
  }, [isListening, isSpeaking, state]);

  const dot =
    state === "error"
      ? styles.error
      : state === "listening"
        ? styles.listening
        : state === "speaking"
          ? styles.speaking
          : state === "ready"
            ? styles.ready
            : "";

  const badgeLabel =
    voiceMode === "server"
      ? "Server voice loop"
      : defaultMode === "auto"
        ? "Client voice loop (auto)"
        : "Client voice loop";

  const testPhrase =
    voiceMode === "server"
      ? "Hi, I'm ADVoi. Server voice is active."
      : "Hi, I'm ADVoi. Kokoro is running on your device.";

  return (
    <section className={styles.panel}>
      <span className={styles.badge}>{badgeLabel}</span>
      <div className={styles.statusRow}>
        <span className={`${styles.dot} ${dot}`} aria-hidden />
        <p className={styles.status}>{status}</p>
      </div>
      {transcript ? <p className={styles.transcript}>You: {transcript}</p> : null}
      {activeAgent ? (
        <p className={styles.agentBadge}>
          Agent: {activeAgent}
          {activeSystems.length ? ` · Systems: ${activeSystems.join(", ")}` : ""}
        </p>
      ) : null}
      {isListening && sttMode === "parakeet" ? (
        <p className={styles.micLevel} aria-live="polite">
          Mic level: {micLevel >= 0.006 ? "hearing you" : micLevel > 0.001 ? "quiet - speak up" : "waiting for audio..."}
        </p>
      ) : null}
      <div className={styles.controls}>
        {voiceMode === "client" ? (
          <select
            className={styles.select}
            value={voice}
            onChange={(e) => setVoice(e.target.value as VoiceId)}
            disabled={isSpeaking || isListening}
          >
            {WARM_VOICES.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        ) : null}
        <button
          type="button"
          className={styles.primary}
          disabled={isSpeaking || state === "thinking"}
          onClick={() => void toggleListening()}
        >
          {isListening ? "Stop" : "Listen"}
        </button>
        <button
          type="button"
          className={styles.secondary}
          disabled={isSpeaking || isListening}
          onClick={() => void speak(testPhrase)}
        >
          Test voice
        </button>
      </div>
      <div className={styles.typeRow}>
        <input
          className={styles.typeInput}
          type="text"
          value={typedLine}
          placeholder="Type a command if the mic fails"
          disabled={isSpeaking || isListening || state === "thinking"}
          onChange={(e) => setTypedLine(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitTypedLine();
          }}
        />
        <button
          type="button"
          className={styles.secondary}
          disabled={!typedLine.trim() || isSpeaking || isListening || state === "thinking"}
          onClick={submitTypedLine}
        >
          Send
        </button>
      </div>
      {agents.length ? (
        <div className={styles.agentRoster}>
          <p className={styles.agentRosterTitle}>Specialist agents</p>
          <ul className={styles.agentList}>
            {agents.map((a) => (
              <li key={a.id} className={styles.agentListItem}>
                <span className={styles.agentName}>{a.name}</span>
                <span className={styles.agentMeta}>
                  {a.frame_id || a.role}
                  {a.cached ? " · cached" : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {voiceMode === "client" && sttBackend && ttsBackend ? (
        <p className={styles.hint}>
          STT: {sttMode === "browser" ? "browser speech" : `Parakeet (${backendLabel(sttBackend)})`}. TTS:{" "}
          {usingBrowserVoice || browserTts ? "browser voice (Kokoro unavailable)" : `Kokoro (${backendLabel(ttsBackend)})`}
          .
        </p>
      ) : null}
      {storageHint ? <p className={styles.warn}>{storageHint}</p> : null}
      {voiceMode === "server" ? (
        <p className={styles.hint}>
          STT: browser speech recognition. TTS: server API (no WebGPU/WASM models in browser).
        </p>
      ) : null}
      {state === "error" || storageHint || voiceMode === "server" ? (
        <div className={styles.storageActions}>
          <button
            type="button"
            className={styles.secondary}
            disabled={clearingCache}
            onClick={() => void handleClearModelCache()}
          >
            {clearingCache ? "Clearing cache..." : "Clear model cache"}
          </button>
        </div>
      ) : null}
      {voiceMode === "client" && isWindows() ? (
        <p className={styles.hint}>
          Windows uses WASM for client models (WebGPU is unstable here). First load downloads ~200MB; cache errors in the console are usually harmless.
        </p>
      ) : null}
      <p className={styles.hint}>
        Replies use the multi-agent API. Try: fleet status, open briefs, systems pulse, queue review.{" "}
        {voiceMode === "server" ? (
          <a className={styles.backLink} href="/voice-local">
            Try client voice
          </a>
        ) : (
          <a className={styles.backLink} href="/voice-server">
            Use server voice (no WebGPU)
          </a>
        )}
        {" · "}
        <a className={styles.backLink} href="/">
          LiveKit PWA
        </a>
      </p>
    </section>
  );
}