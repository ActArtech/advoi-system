"use client";

import { useCallback, useRef, useState } from "react";
import { playSpeechSynthesisFallback } from "./audio";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

function playBlob(blob: Blob): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("playback failed"));
    };
    void audio.play().catch(reject);
  });
}

/** Server-side TTS via ADVoi API (OpenAI-compatible). No WebGPU/WASM in browser. */
export function useServerTTS({
  voice,
  onComplete,
  onError,
  onReady,
}: {
  voice?: string;
  onComplete?: () => void;
  onError?: (msg: string) => void;
  onReady?: () => void;
} = {}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isReady, setIsReady] = useState(true);
  const busy = useRef(false);

  const preload = useCallback(async () => {
    try {
      const resp = await fetch(`${apiBase}/diagnostics/voice`);
      if (!resp.ok) throw new Error(`Voice diagnostics returned ${resp.status}`);
      const data = (await resp.json()) as { checks?: { voice_respond_ready?: boolean } };
      if (!data.checks?.voice_respond_ready) {
        throw new Error("API voice not ready (check LLM API key on server)");
      }
      setIsReady(true);
      onReady?.();
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Server voice check failed");
      setIsReady(false);
    }
  }, [onError, onReady]);

  const speak = useCallback(
    async (text: string) => {
      if (!text?.trim() || busy.current) return;
      busy.current = true;
      setIsSpeaking(true);
      try {
        const resp = await fetch(`${apiBase}/voice/speak`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice }),
        });
        if (!resp.ok) {
          const detail = await resp.text();
          throw new Error(detail || `Server TTS returned ${resp.status}`);
        }
        await playBlob(await resp.blob());
      } catch (e) {
        onError?.(e instanceof Error ? e.message : "Server TTS failed");
        await playSpeechSynthesisFallback(text);
      } finally {
        busy.current = false;
        setIsSpeaking(false);
        onComplete?.();
      }
    },
    [voice, onComplete, onError],
  );

  return { speak, isSpeaking, isReady, preload, usingBrowserVoice: false, mode: "server" as const };
}