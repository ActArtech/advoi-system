"use client";

import { useCallback, useRef, useState } from "react";
import type { VoiceId } from "./types";
import { playSpeechSynthesisFallback } from "./audio";
import { warmTextForTTS } from "./warmth";

const MODEL_ID = "onnx-community/Kokoro-82M-v1.0-ONNX";
let sharedTts: Promise<import("kokoro-js").KokoroTTS> | null = null;

async function loadTts() {
  if (!sharedTts) {
    sharedTts = (async () => {
      const { KokoroTTS } = await import("kokoro-js");
      const device = typeof navigator !== "undefined" && "gpu" in navigator ? "webgpu" : "wasm";
      return KokoroTTS.from_pretrained(MODEL_ID, {
        dtype: device === "webgpu" ? "fp32" : "q8",
        device,
      });
    })();
  }
  return sharedTts;
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
}: {
  voice?: VoiceId;
  speed?: number;
  onComplete?: () => void;
  onError?: (msg: string) => void;
} = {}) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const busy = useRef(false);

  const preload = useCallback(async () => {
    try {
      await loadTts();
      setIsReady(true);
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Kokoro preload failed");
    }
  }, [onError]);

  const speak = useCallback(
    async (text: string) => {
      if (!text?.trim() || busy.current) return;
      busy.current = true;
      setIsSpeaking(true);
      try {
        const { KokoroTTS, TextSplitterStream } = await import("kokoro-js");
        const tts = await loadTts();
        setIsReady(true);
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
        onError?.(e instanceof Error ? e.message : "TTS failed");
        await playSpeechSynthesisFallback(text);
      } finally {
        busy.current = false;
        setIsSpeaking(false);
        onComplete?.();
      }
    },
    [voice, speed, onComplete, onError],
  );

  return { speak, isSpeaking, isReady, preload };
}