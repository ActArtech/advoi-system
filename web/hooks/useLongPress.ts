"use client";

import { useCallback, useRef } from "react";

type UseLongPressOptions = {
  delayMs?: number;
  disabled?: boolean;
};

/**
 * Pointer long-press for mobile slice actions (e.g. squad dispatch).
 */
export function useLongPress(
  onLongPress: () => void,
  { delayMs = 500, disabled }: UseLongPressOptions = {},
) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const firedRef = useRef(false);

  const clear = useCallback(() => {
    if (timerRef.current != null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const onPointerDown = useCallback(() => {
    if (disabled) return;
    firedRef.current = false;
    clear();
    timerRef.current = setTimeout(() => {
      firedRef.current = true;
      onLongPress();
    }, delayMs);
  }, [clear, delayMs, disabled, onLongPress]);

  const onPointerUp = useCallback(() => {
    clear();
  }, [clear]);

  const onPointerLeave = useCallback(() => {
    clear();
  }, [clear]);

  const onPointerCancel = useCallback(() => {
    clear();
  }, [clear]);

  const consumeLongPress = useCallback(() => firedRef.current, []);

  return {
    onPointerDown,
    onPointerUp,
    onPointerLeave,
    onPointerCancel,
    consumeLongPress,
  };
}