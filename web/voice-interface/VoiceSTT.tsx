"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ParakeetModel } from "parakeet.js";
import { rmsEnergy, startMicCapture } from "./audio";
import { withBackendFallback, type ModelBackend } from "./modelBackend";
import type { TranscriptHandler } from "./types";

const MODEL_KEY = "parakeet-tdt-0.6b-v3";
const modelCache = new Map<ModelBackend, Promise<ParakeetModel>>();

async function loadModel(backend: ModelBackend): Promise<ParakeetModel> {
  let pending = modelCache.get(backend);
  if (!pending) {
    pending = (async () => {
      const { fromHub } = await import("parakeet.js");
      return fromHub(MODEL_KEY, { backend, encoderQuant: "fp32", decoderQuant: "int8" });
    })();
    modelCache.set(backend, pending);
  }
  return pending;
}

export function useVoiceSTT({
  onTranscript,
  onError,
  onBackendReady,
}: {
  onTranscript: TranscriptHandler;
  onError?: (msg: string) => void;
  onBackendReady?: (backend: ModelBackend) => void;
}) {
  const [isListening, setIsListening] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const modelRef = useRef<ParakeetModel | null>(null);
  const stopMicRef = useRef<(() => void) | null>(null);
  const listening = useRef(false);
  const speechMs = useRef(0);
  const silenceMs = useRef(0);
  const hadSpeech = useRef(false);
  const lastPartial = useRef("");

  useEffect(() => {
    let cancelled = false;
    withBackendFallback(loadModel)
      .then(({ value, backend }) => {
        if (!cancelled) {
          modelRef.current = value;
          onBackendReady?.(backend);
          setIsReady(true);
        }
      })
      .catch((e) => onError?.(e instanceof Error ? e.message : "Parakeet load failed"));
    return () => {
      cancelled = true;
    };
  }, [onError, onBackendReady]);

  const stopListening = useCallback(() => {
    listening.current = false;
    stopMicRef.current?.();
    stopMicRef.current = null;
    setIsListening(false);
    speechMs.current = 0;
    silenceMs.current = 0;
    hadSpeech.current = false;
    lastPartial.current = "";
  }, []);

  const toggleListening = useCallback(async () => {
    if (listening.current) {
      stopListening();
      return;
    }
    try {
      const model =
        modelRef.current ?? (await withBackendFallback(loadModel)).value;
      modelRef.current = model;
      setIsReady(true);
      const transcriber = model.createStreamingTranscriber({ returnConfidences: true, sampleRate: 16000 });
      listening.current = true;
      setIsListening(true);

      stopMicRef.current = await startMicCapture(async (chunk) => {
        if (!listening.current) return;
        const speaking = rmsEnergy(chunk) >= 0.012;
        if (speaking) {
          speechMs.current += 320;
          silenceMs.current = 0;
          hadSpeech.current = true;
        } else if (hadSpeech.current) {
          silenceMs.current += 320;
        }
        if (!speaking && speechMs.current < 400) return;

        const result = await transcriber.processChunk(chunk);
        const partial = result.text.trim();
        if (partial && partial !== lastPartial.current) {
          lastPartial.current = partial;
          onTranscript(partial, false);
        }
        if (hadSpeech.current && silenceMs.current >= 900 && speechMs.current >= 400) {
          const final = transcriber.finalize();
          if (final.text.trim()) onTranscript(final.text.trim(), true);
          transcriber.reset();
          speechMs.current = 0;
          silenceMs.current = 0;
          hadSpeech.current = false;
          lastPartial.current = "";
        }
      });
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Mic failed");
      stopListening();
    }
  }, [onTranscript, onError, stopListening]);

  useEffect(() => () => stopListening(), [stopListening]);

  return { isListening, isReady, toggleListening, stopListening };
}