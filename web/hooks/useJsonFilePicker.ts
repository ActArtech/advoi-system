"use client";

import { useCallback, useRef } from "react";

type UseJsonFilePickerOptions = {
  onJson: (raw: string, filename: string) => void;
  onError?: (message: string) => void;
};

/**
 * Hidden file input for JSON import (replaces window.prompt paste flow).
 */
export function useJsonFilePicker({ onJson, onError }: UseJsonFilePickerOptions) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const openPicker = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const onChange = useCallback(
    (ev: React.ChangeEvent<HTMLInputElement>) => {
      const file = ev.target.files?.[0];
      ev.target.value = "";
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const raw = typeof reader.result === "string" ? reader.result : "";
        if (!raw.trim()) {
          onError?.("Empty file");
          return;
        }
        onJson(raw, file.name);
      };
      reader.onerror = () => onError?.("Could not read file");
      reader.readAsText(file);
    },
    [onJson, onError],
  );

  return { openPicker, inputRef, onChange };
}