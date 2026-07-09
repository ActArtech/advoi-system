"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ParakeetModel } from "parakeet.js";
import { rmsEnergy, startMicCapture } from "./audio";
import { withBackendFallback, type ModelBackend } from "./modelBackend";
import { formatModelLoadError } from "./storageProbe";
import { useBrowserSTT } from "./useBrowserSTT";
import type { TranscriptHandler } from "./types";

const MODEL_KEY = "parakeet-tdt-0.6b-v3";
const SPEECH_RMS_THRESHOLD = 0.006;
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

export type SttMode = "parakeet" | "browser" | "loading";

export function useVoiceSTT({
  onTranscript,
  onError,
  onBackendReady,
  onMicLevel,
  preferBrowser = false,
}: {
  onTranscript: TranscriptHandler;
  onError?: (msg: string) => void;
  onBackendReady?: (backend: ModelBackend) => void;
  onMicLevel?: (rms: number) => void;
  /** Skip Parakeet download; use browser Web Speech API only (server voice path). */
  preferBrowser?: boolean;
}) {
  const [sttMode, setSttMode] = useState<SttMode>("loading");
  const [isReady, setIsReady] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const modelRef = useRef<ParakeetModel | null>(null);
  const stopMicRef = useRef<(() => void) | null>(null);
  const listening = useRef(false);
  const speechMs = useRef(0);
  const silenceMs = useRef(0);
  const hadSpeech = useRef(false);
  const lastPartial = useRef("");

  const browser = useBrowserSTT({ onTranscript, onError });

  useEffect(() => {
    if (preferBrowser) {
      setSttMode("browser");
      if (browser.isReady) {
        setIsReady(true);
        onBackendReady?.("wasm");
      } else {
        onError?.("Browser speech recognition unavailable. Use typed input or Chrome desktop.");
      }
      return;
    }

    let cancelled = false;
    withBackendFallback(loadModel)
      .then(({ value, backend }) => {
        if (cancelled) return;
        modelRef.current = value;
        onBackendReady?.(backend);
        setSttMode("parakeet");
        setIsReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        if (browser.isReady) {
          setSttMode("browser");
          setIsReady(true);
        } else {
          setSttMode("browser");
          onError?.(formatModelLoadError(new Error("Parakeet failed to load")));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [onError, onBackendReady, browser.isReady, preferBrowser]);

  const stopParakeetListening = useCallback(() => {
    listening.current = false;
    stopMicRef.current?.();
    stopMicRef.current = null;
    speechMs.current = 0;
    silenceMs.current = 0;
    hadSpeech.current = false;
    lastPartial.current = "";
    setMicLevel(0);
  }, []);

  const toggleParakeetListening = useCallback(async () => {
    if (listening.current) {
      stopParakeetListening();
      return false;
    }
    const model =
      modelRef.current ?? (await withBackendFallback(loadModel)).value;
    modelRef.current = model;
    const transcriber = model.createStreamingTranscriber({ returnConfidences: true, sampleRate: 16000 });
    listening.current = true;

    stopMicRef.current = await startMicCapture(
      async (chunk) => {
      if (!listening.current) return;
      const speaking = rmsEnergy(chunk) >= SPEECH_RMS_THRESHOLD;
      if (speaking) {
        speechMs.current += 320;
        silenceMs.current = 0;
        hadSpeech.current = true;
      } else if (hadSpeech.current) {
        silenceMs.current += 320;
      }

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
    },
      (rms) => {
        setMicLevel(rms);
        onMicLevel?.(rms);
      },
    );
    return true;
  }, [onMicLevel, onTranscript, stopParakeetListening]);

  const [isListening, setIsListening] = useState(false);

  const toggleListening = useCallback(async () => {
    if (sttMode === "browser" || !modelRef.current) {
      if (browser.isListening) {
        browser.stopListening();
        setIsListening(false);
        return;
      }
      browser.toggleListening();
      setIsListening(true);
      return;
    }
    if (listening.current) {
      stopParakeetListening();
      setIsListening(false);
      return;
    }
    try {
      await toggleParakeetListening();
      setIsListening(true);
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Mic failed");
      if (browser.isReady) {
        setSttMode("browser");
        browser.toggleListening();
        setIsListening(true);
      }
    }
  }, [
    browser,
    onError,
    sttMode,
    stopParakeetListening,
    toggleParakeetListening,
  ]);

  const stopListening = useCallback(() => {
    stopParakeetListening();
    browser.stopListening();
    setIsListening(false);
  }, [browser, stopParakeetListening]);

  useEffect(() => () => stopListening(), [stopListening]);

  return {
    isListening: isListening || browser.isListening,
    isReady: isReady || browser.isReady,
    toggleListening,
    stopListening,
    sttMode,
    micLevel,
  };
}