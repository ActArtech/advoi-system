"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { TranscriptHandler } from "./types";

type BrowserSpeechResult = {
  isFinal: boolean;
  0?: { transcript?: string };
};

type BrowserSpeechRecognitionEvent = {
  resultIndex: number;
  results: BrowserSpeechResult[];
};

type BrowserSpeechRecognitionErrorEvent = {
  error: string;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((ev: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((ev: BrowserSpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionCtor = new () => BrowserSpeechRecognition;

function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Browser Web Speech API fallback when Parakeet cannot load. */
export function useBrowserSTT({
  onTranscript,
  onError,
}: {
  onTranscript: TranscriptHandler;
  onError?: (msg: string) => void;
}) {
  const [isListening, setIsListening] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const recRef = useRef<BrowserSpeechRecognition | null>(null);
  const wantListening = useRef(false);

  useEffect(() => {
    setIsReady(getSpeechRecognition() != null);
  }, []);

  const stopListening = useCallback(() => {
    wantListening.current = false;
    recRef.current?.stop();
    recRef.current = null;
    setIsListening(false);
  }, []);

  const startListening = useCallback(() => {
    const Ctor = getSpeechRecognition();
    if (!Ctor) {
      onError?.("Browser speech recognition is not available in this browser.");
      wantListening.current = false;
      setIsListening(false);
      return;
    }

    const rec = new Ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.onresult = (ev: BrowserSpeechRecognitionEvent) => {
      let interim = "";
      let finalText = "";
      for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
        const chunk = ev.results[i]?.[0]?.transcript?.trim() ?? "";
        if (!chunk) continue;
        if (ev.results[i].isFinal) finalText = chunk;
        else interim = chunk;
      }
      if (interim) onTranscript(interim, false);
      if (finalText) onTranscript(finalText, true);
    };
    rec.onerror = (ev: BrowserSpeechRecognitionErrorEvent) => {
      if (ev.error === "aborted" || ev.error === "no-speech") return;
      onError?.(`Speech recognition: ${ev.error}`);
      stopListening();
    };
    rec.onend = () => {
      recRef.current = null;
      if (wantListening.current) {
        window.setTimeout(() => {
          if (wantListening.current) startListening();
        }, 120);
      } else {
        setIsListening(false);
      }
    };
    recRef.current = rec;
    setIsListening(true);
    rec.start();
  }, [onError, onTranscript, stopListening]);

  const toggleListening = useCallback(() => {
    if (wantListening.current) {
      stopListening();
      return;
    }
    wantListening.current = true;
    startListening();
  }, [startListening, stopListening]);

  useEffect(() => () => stopListening(), [stopListening]);

  return { isListening, isReady, toggleListening, stopListening, mode: "browser" as const };
}