"use client";

import { useCallback, useRef, useState } from "react";
import type { VoiceId } from "./types";
import { playSpeechSynthesisFallback } from "./audio";
import { warmTextForTTS } from "./warmth";
import { withBackendFallback, type ModelBackend } from "./modelBackend";
import { formatModelLoadError } from "./storageProbe";

const MODEL_ID = "onnx-community/Kokoro-82M-v1.0-ONNX";
const ttsCache = new Map<ModelBackend, Promise<import("kokoro-js").KokoroTTS>>();

async function loadTts(backend: ModelBackend) {
  let pending = ttsCache.get(backend);
  if (!pending) {
    pending = (async () => {
      const { KokoroTTS } = await import("kokoro-js");
      return KokoroTTS.from_pretrained(MODEL_ID, {
        dtype: backend === "webgpu" ? "fp32" : "q8",
        device: backend,
      });
    })();
    ttsCache.set(backend, pending);
  }
  return pending;
}

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

export function useVoiceTTS({
  voice = "af_heart",
  speed = 1.2,
  onComplete,
  onError,
  onBackendReady,
  onFallback,
  reportPreloadErrors = true,
}: {
  voice?: VoiceId;
  speed?: number;
  onComplete?: () => void;
  onError?: (msg: string) => void;
  onBackendReady?: (backend: ModelBackend) => void;
  onFallback?: () => void;
  /** When false, preload throws without calling onError (auto server fallback). */
  reportPreloadErrors?: boolean;
} = {}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [usingBrowserVoice, setUsingBrowserVoice] = useState(false);
  const busy = useRef(false);
  const activeBackend = useRef<ModelBackend | null>(null);

  const preload = useCallback(async () => {
    try {
      const { backend, value } = await withBackendFallback(loadTts);
      await value;
      activeBackend.current = backend;
      onBackendReady?.(backend);
      setIsReady(true);
      setUsingBrowserVoice(false);
    } catch (e) {
      const msg = formatModelLoadError(e);
      if (reportPreloadErrors) onError?.(msg);
      throw e instanceof Error ? e : new Error(msg);
    }
  }, [onError, onBackendReady, reportPreloadErrors]);

  const speak = useCallback(
    async (text: string) => {
      if (!text?.trim() || busy.current) return;
      busy.current = true;
      setIsSpeaking(true);
      try {
        const backend = activeBackend.current ?? (await withBackendFallback(loadTts)).backend;
        activeBackend.current = backend;
        const { TextSplitterStream } = await import("kokoro-js");
        const tts = await loadTts(backend);
        setIsReady(true);
        setUsingBrowserVoice(false);
        const splitter = new TextSplitterStream();
        const stream = tts.stream(splitter, { voice, speed });
        const playback = (async () => {
          for await (const { audio } of stream) {
            await playBlob(audio.toBlob());
          }
        })();
        splitter.push(warmTextForTTS(text));
        splitter.close();
        await playback;
      } catch (e) {
        onError?.(formatModelLoadError(e));
        setUsingBrowserVoice(true);
        onFallback?.();
        await playSpeechSynthesisFallback(text);
      } finally {
        busy.current = false;
        setIsSpeaking(false);
        onComplete?.();
      }
    },
    [voice, speed, onComplete, onError, onFallback],
  );

  return { speak, isSpeaking, isReady, usingBrowserVoice, preload };
}