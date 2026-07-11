"use client";

import { useEffect } from "react";
import type { AgentSliceModel } from "@/lib/agents/types";

type SliceKeyboardHandlers = {
  slices: AgentSliceModel[];
  busy: boolean;
  failedCount: number;
  enabled?: boolean;
  onRunSlice: (slice: AgentSliceModel) => void;
  onRetryFailed: () => void;
  onCancel: () => void;
  onToggleMulti: () => void;
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

/**
 * Agents tab keyboard shortcuts:
 * 1-6 run slice, r retry failed, Escape cancel, m toggle multi-select.
 */
export function useSliceKeyboard({
  slices,
  busy,
  failedCount,
  enabled = true,
  onRunSlice,
  onRetryFailed,
  onCancel,
  onToggleMulti,
}: SliceKeyboardHandlers) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (ev: KeyboardEvent) => {
      if (isTypingTarget(ev.target)) return;

      if (ev.key === "Escape" && busy) {
        ev.preventDefault();
        onCancel();
        return;
      }

      if (busy) return;

      const digit = ev.key;
      if (digit >= "1" && digit <= "6") {
        const idx = Number(digit) - 1;
        const slice = slices[idx];
        if (slice) {
          ev.preventDefault();
          onRunSlice(slice);
        }
        return;
      }

      if ((ev.key === "r" || ev.key === "R") && failedCount > 0) {
        ev.preventDefault();
        onRetryFailed();
        return;
      }

      if (ev.key === "m" || ev.key === "M") {
        ev.preventDefault();
        onToggleMulti();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [slices, busy, failedCount, enabled, onRunSlice, onRetryFailed, onCancel, onToggleMulti]);
}