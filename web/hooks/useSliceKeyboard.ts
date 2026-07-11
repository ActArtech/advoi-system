"use client";

import { useEffect } from "react";
import type { AgentSliceModel } from "@/lib/agents/types";

type SliceKeyboardHandlers = {
  slices: AgentSliceModel[];
  busy: boolean;
  failedCount: number;
  selectedCount?: number;
  chainSuggestionCount?: number;
  queueDepth?: number;
  enabled?: boolean;
  onRunSlice: (slice: AgentSliceModel) => void;
  onRetryFailed: () => void;
  onCancel: () => void;
  onToggleMulti: () => void;
  onRunAll?: () => void;
  onRunSelected?: () => void;
  onRunChainSuggestion?: () => void;
  onOpenQueue?: () => void;
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

/**
 * Agents tab keyboard shortcuts:
 * 1-6 run slice, Enter run selected/all, C run chain suggestion,
 * Q open queue, R retry failed, Escape cancel, M toggle multi-select.
 */
export function useSliceKeyboard({
  slices,
  busy,
  failedCount,
  selectedCount = 0,
  chainSuggestionCount = 0,
  queueDepth = 0,
  enabled = true,
  onRunSlice,
  onRetryFailed,
  onCancel,
  onToggleMulti,
  onRunAll,
  onRunSelected,
  onRunChainSuggestion,
  onOpenQueue,
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

      if (ev.key === "Enter") {
        if (selectedCount > 0 && onRunSelected) {
          ev.preventDefault();
          onRunSelected();
          return;
        }
        if (onRunAll) {
          ev.preventDefault();
          onRunAll();
        }
        return;
      }

      if ((ev.key === "c" || ev.key === "C") && chainSuggestionCount > 0 && onRunChainSuggestion) {
        ev.preventDefault();
        onRunChainSuggestion();
        return;
      }

      if ((ev.key === "q" || ev.key === "Q") && queueDepth > 0 && onOpenQueue) {
        ev.preventDefault();
        onOpenQueue();
        return;
      }

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
  }, [
    slices,
    busy,
    failedCount,
    selectedCount,
    chainSuggestionCount,
    queueDepth,
    enabled,
    onRunSlice,
    onRetryFailed,
    onCancel,
    onToggleMulti,
    onRunAll,
    onRunSelected,
    onRunChainSuggestion,
    onOpenQueue,
  ]);
}