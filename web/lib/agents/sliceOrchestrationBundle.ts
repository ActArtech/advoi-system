/**
 * Combined export/import for presets, chains, history, and run mode.
 * Python mirror in tests/test_agent_slices.py.
 */

import type { UserPresetChain } from "./customUserChains";
import type { UserSlicePreset } from "./customUserPresets";
import { importUserChainsJson } from "./customUserChains";
import { importUserPresetsJson } from "./customUserPresets";
import { importRunLogJson, type SliceRunLogEntry } from "./sliceRunLog";
import type { RunExecutionMode } from "./types";

export const BUNDLE_VERSION = 1;

export type OrchestrationBundle = {
  version: typeof BUNDLE_VERSION;
  exportedAt: number;
  presets: UserSlicePreset[];
  chains: UserPresetChain[];
  history: SliceRunLogEntry[];
  runMode?: RunExecutionMode;
};

export type OrchestrationBundleImport = {
  presets: UserSlicePreset[];
  chains: UserPresetChain[];
  history: SliceRunLogEntry[];
  runMode: RunExecutionMode | null;
  /** Which sections were present in the imported file */
  importedSections: ("presets" | "chains" | "history" | "runMode")[];
};

const VALID_MODES: RunExecutionMode[] = ["parallel", "wave", "stagger"];

function parseRunMode(value: unknown): RunExecutionMode | null {
  if (typeof value === "string" && VALID_MODES.includes(value as RunExecutionMode)) {
    return value as RunExecutionMode;
  }
  return null;
}

export function exportOrchestrationBundle(input: {
  presets: UserSlicePreset[];
  chains: UserPresetChain[];
  history: SliceRunLogEntry[];
  runMode?: RunExecutionMode;
}): string {
  const bundle: OrchestrationBundle = {
    version: BUNDLE_VERSION,
    exportedAt: Date.now(),
    presets: input.presets,
    chains: input.chains,
    history: input.history,
    runMode: input.runMode,
  };
  return JSON.stringify(bundle, null, 2);
}

/** Parse bundle or legacy single-section JSON (presets / chains / history only). */
export function parseOrchestrationImport(json: string): OrchestrationBundleImport {
  const parsed = JSON.parse(json) as Record<string, unknown>;
  if (!parsed || typeof parsed !== "object") {
    throw new Error("Invalid JSON");
  }

  const sections: OrchestrationBundleImport["importedSections"] = [];
  let presets: UserSlicePreset[] = [];
  let chains: UserPresetChain[] = [];
  let history: SliceRunLogEntry[] = [];
  let runMode: RunExecutionMode | null = null;

  const isBundle =
    "presets" in parsed || "chains" in parsed || "history" in parsed || "entries" in parsed;

  if (isBundle && ("presets" in parsed || "chains" in parsed || "history" in parsed)) {
    if (Array.isArray(parsed.presets)) {
      presets = importUserPresetsJson(JSON.stringify({ presets: parsed.presets }));
      sections.push("presets");
    }
    if (Array.isArray(parsed.chains)) {
      chains = importUserChainsJson(JSON.stringify({ chains: parsed.chains }));
      sections.push("chains");
    }
    if (Array.isArray(parsed.history)) {
      history = importRunLogJson(JSON.stringify({ entries: parsed.history }));
      sections.push("history");
    }
    const mode = parseRunMode(parsed.runMode);
    if (mode) {
      runMode = mode;
      sections.push("runMode");
    }
    return { presets, chains, history, runMode, importedSections: sections };
  }

  if (Array.isArray(parsed.presets)) {
    presets = importUserPresetsJson(json);
    sections.push("presets");
    return { presets, chains, history, runMode, importedSections: sections };
  }

  if (Array.isArray(parsed.chains)) {
    chains = importUserChainsJson(json);
    sections.push("chains");
    return { presets, chains, history, runMode, importedSections: sections };
  }

  if (Array.isArray(parsed.entries)) {
    history = importRunLogJson(json);
    sections.push("history");
    return { presets, chains, history, runMode, importedSections: sections };
  }

  throw new Error("Unrecognized orchestration JSON format");
}

export function describeBundleImport(sections: OrchestrationBundleImport["importedSections"]): string {
  if (sections.length === 0) return "Nothing imported";
  const labels: Record<string, string> = {
    presets: "presets",
    chains: "chains",
    history: "history",
    runMode: "run mode",
  };
  return `Imported ${sections.map((s) => labels[s]).join(", ")}`;
}