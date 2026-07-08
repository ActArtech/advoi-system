"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./VoiceLoop.module.css";
import { useVoiceSTT } from "./VoiceSTT";
import { useVoiceTTS } from "./VoiceTTS";
import { isConfirmPhrase, mirrorPhrases, stripEmDash } from "./warmth";
import { backendLabel, isWindows, type ModelBackend } from "./modelBackend";
import { WARM_VOICES, type VoiceId } from "./types";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

type LoopState = "idle" | "loading" | "ready" | "listening" | "thinking" | "speaking" | "error";

type VoiceIntentResponse = {
  action?: string;
  frame_id?: string;
  confirmed?: boolean | null;
  preview?: { spoken_summary?: string; status?: string };
};

function isFrameIntent(data: VoiceIntentResponse): data is VoiceIntentResponse & { frame_id: string } {
  const frameId = data.frame_id?.trim();
  if (!frameId) return false;
  return data.action === "frame";
}

function webGpuAvailable(): boolean {
  if (typeof navigator === "undefined") return false;
  return "gpu" in navigator;
}

export function VoiceLoop() {
  const [state, setState] = useState<LoopState>("loading");
  const [status, setStatus] = useState("Loading Kokoro and Parakeet models...");
  const [webGpu, setWebGpu] = useState<boolean | null>(null);
  const [sttBackend, setSttBackend] = useState<ModelBackend | null>(null);
  const [ttsBackend, setTtsBackend] = useState<ModelBackend | null>(null);
  const [browserTts, setBrowserTts] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voice, setVoice] = useState<VoiceId>("af_heart");
  const busy = useRef(false);
  const pendingFrame = useRef<string | null>(null);

  const onError = useCallback((msg: string) => {
    setState("error");
    setStatus(msg);
  }, []);

  const { speak, isSpeaking, preload, usingBrowserVoice } = useVoiceTTS({
    voice,
    speed: 1.2,
    onError,
    onBackendReady: setTtsBackend,
    onFallback: () => setBrowserTts(true),
  });

  const respond = useCallback(
    async (text: string) => {
      if (!text.trim() || busy.current) return;
      busy.current = true;
      setState("thinking");
      setStatus("Thinking...");
      const phrases = mirrorPhrases(text);
      try {
        let spoken = "";

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
                if (
                  intentData.preview?.status === "confirmation_required" ||
                  (intentData.frame_id === "queue_deep_review" && !intentData.confirmed)
                ) {
                  pendingFrame.current = intentData.frame_id;
                }
              } else {
                const refresh = intentData.frame_id === "fleet_status";
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
            spoken = stripEmDash(String((await resp.json()).spoken || ""));
          } else {
            spoken = `I heard: ${text}. Connect the API for agent replies.`;
          }
        }

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

  const { isListening, toggleListening } = useVoiceSTT({
    onTranscript,
    onError,
    onBackendReady: setSttBackend,
  });

  useEffect(() => {
    setWebGpu(webGpuAvailable());
  }, []);

  useEffect(() => {
    void preload().then(() => {
      setState("ready");
      const accel = ttsBackend ? backendLabel(ttsBackend) : webGpu ? "WebGPU" : "WASM";
      setStatus(`Ready (Kokoro ${accel}). Tap listen and speak.`);
    });
  }, [preload, webGpu, ttsBackend]);

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

  return (
    <section className={styles.panel}>
      <span className={styles.badge}>Client voice loop</span>
      <div className={styles.statusRow}>
        <span className={`${styles.dot} ${dot}`} aria-hidden />
        <p className={styles.status}>{status}</p>
      </div>
      {transcript ? <p className={styles.transcript}>You: {transcript}</p> : null}
      <div className={styles.controls}>
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
          onClick={() => void speak("Hi, I'm ADVoi. Kokoro is running on your device.")}
        >
          Test voice
        </button>
      </div>
      {sttBackend && ttsBackend ? (
        <p className={styles.hint}>
          STT: Parakeet ({backendLabel(sttBackend)}). TTS:{" "}
          {usingBrowserVoice || browserTts ? "browser voice (Kokoro unavailable)" : `Kokoro (${backendLabel(ttsBackend)})`}
          .
        </p>
      ) : null}
      {isWindows() ? (
        <p className={styles.hint}>
          Windows uses WASM for client models (WebGPU is unstable here). First load downloads ~200MB; cache errors in the console are usually harmless.
        </p>
      ) : webGpu === false ? (
        <p className={styles.hint}>
          WebGPU not detected. Models use WASM (slower). Desktop Chrome recommended; iOS may not support Path B yet.
        </p>
      ) : null}
      <p className={styles.hint}>
        Parakeet STT and Kokoro TTS run in your browser. Replies use the multi-agent API when available.
        Try: fleet status, open briefs, queue review.{" "}
        <a className={styles.backLink} href="/">
          Back to LiveKit PWA
        </a>
      </p>
    </section>
  );
}