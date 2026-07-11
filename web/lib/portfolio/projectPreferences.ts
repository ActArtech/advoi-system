/**
 * Persisted active project and user-defined venture features.
 */

import type { UserProjectFeature } from "./projectModel";

const ACTIVE_VENTURE_KEY = "advoi:active-venture";
const ACTIVE_FUNCTION_KEY = "advoi:active-function";
const USER_FEATURES_KEY = "advoi:user-project-features";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function readActiveVentureId(): string | null {
  if (!canUseStorage()) return null;
  try {
    return window.localStorage.getItem(ACTIVE_VENTURE_KEY);
  } catch {
    return null;
  }
}

export function saveActiveVentureId(ventureId: string | null): void {
  if (!canUseStorage()) return;
  try {
    if (ventureId) {
      window.localStorage.setItem(ACTIVE_VENTURE_KEY, ventureId);
    } else {
      window.localStorage.removeItem(ACTIVE_VENTURE_KEY);
    }
  } catch {
    // ignore
  }
}

export function readActiveFunctionId(): string | null {
  if (!canUseStorage()) return null;
  try {
    return window.localStorage.getItem(ACTIVE_FUNCTION_KEY);
  } catch {
    return null;
  }
}

export function saveActiveFunctionId(functionId: string | null): void {
  if (!canUseStorage()) return;
  try {
    if (functionId) {
      window.localStorage.setItem(ACTIVE_FUNCTION_KEY, functionId);
    } else {
      window.localStorage.removeItem(ACTIVE_FUNCTION_KEY);
    }
  } catch {
    // ignore
  }
}

export function readUserProjectFeatures(): UserProjectFeature[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(USER_FEATURES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (row): row is UserProjectFeature =>
        typeof row === "object" &&
        row !== null &&
        typeof (row as UserProjectFeature).id === "string" &&
        typeof (row as UserProjectFeature).ventureId === "string" &&
        typeof (row as UserProjectFeature).label === "string",
    );
  } catch {
    return [];
  }
}

export function saveUserProjectFeatures(rows: UserProjectFeature[]): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(USER_FEATURES_KEY, JSON.stringify(rows));
  } catch {
    // ignore
  }
}

export function appendUserProjectFeature(feature: UserProjectFeature): UserProjectFeature[] {
  const rows = [...readUserProjectFeatures(), feature];
  saveUserProjectFeatures(rows);
  return rows;
}