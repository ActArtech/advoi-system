/**
 * Project selector model — keep Python mirror in tests/test_project_selector.py in sync.
 */

export type ProjectFunctionKind = "frame" | "bet" | "custom";

export type ProjectFunction = {
  id: string;
  label: string;
  kind: ProjectFunctionKind;
  frame_id?: string;
  status?: string;
};

export type VentureProject = {
  id: string;
  name: string;
  status: string;
  fleet_slug?: string | null;
  squads: string[];
  functions: ProjectFunction[];
};

export type ProjectsCatalog = {
  ventures: VentureProject[];
  active_venture_id?: string | null;
  active_fleet_slug?: string | null;
  gate_active_slug?: string | null;
  source?: string | null;
};

export const PROJECT_SWITCH_EVENT = "advoi:project-switch";

export type ProjectSwitchDetail = {
  ventureId: string;
  ventureName?: string;
  functionId?: string;
  frameId?: string;
  source?: string;
};

export type UserProjectFeature = {
  id: string;
  ventureId: string;
  label: string;
  note?: string;
};

export function mergeUserFeatures(
  venture: VentureProject,
  userFeatures: readonly UserProjectFeature[],
): ProjectFunction[] {
  const custom = userFeatures
    .filter((row) => row.ventureId === venture.id)
    .map((row) => ({
      id: row.id,
      label: row.label,
      kind: "custom" as const,
    }));
  return [...venture.functions, ...custom];
}

export function ventureById(
  catalog: ProjectsCatalog | null | undefined,
  ventureId: string | null | undefined,
): VentureProject | null {
  if (!catalog || !ventureId) return null;
  return catalog.ventures.find((row) => row.id === ventureId) ?? null;
}

/** When portfolio lists squad ids but registry venture_id differs, map by id. */
const VENTURE_SQUAD_FALLBACK_IDS: Record<string, readonly string[]> = {
  "gem-dev-shop": ["venture-squad", "fleet-squad", "briefs-squad", "review-squad"],
};

/**
 * Scope Agents tab squads to the project bar venture.
 * Prefer venture_id match; else portfolio squad ids; else known fallbacks; else all.
 */
export function filterSquadsForVenture<T extends { id: string; venture_id?: string }>(
  squads: readonly T[],
  ventureId: string | null | undefined,
  allowedSquadIds?: readonly string[] | null,
): T[] {
  if (!ventureId) return [...squads];
  const scoped = squads.filter((row) => row.venture_id === ventureId);
  if (scoped.length > 0) return scoped;

  if (allowedSquadIds && allowedSquadIds.length > 0) {
    const allow = new Set(allowedSquadIds);
    const byId = squads.filter((row) => allow.has(row.id));
    if (byId.length > 0) return byId;
  }

  const fallback = VENTURE_SQUAD_FALLBACK_IDS[ventureId];
  if (fallback) {
    const allow = new Set(fallback);
    const byFallback = squads.filter((row) => allow.has(row.id));
    if (byFallback.length > 0) return byFallback;
  }

  return [...squads];
}

export function projectSelectorLabel(
  venture: VentureProject | null,
  functionId?: string | null,
): string {
  if (!venture) return "Select project";
  if (!functionId) return venture.name;
  const fn = venture.functions.find((row) => row.id === functionId);
  return fn ? `${venture.name} · ${fn.label}` : venture.name;
}

export function makeUserFeatureId(label: string): string {
  const slug = label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `custom-${slug || "feature"}-${Date.now().toString(36)}`;
}

/** Fleet fm-bridge slug: project bar wins over FirstMate profile snapshot. */
export function resolveFleetProjectSlug(
  activeVenture: VentureProject | null | undefined,
  fleetProfileSlug?: string | null,
): string | null {
  const fromBar = activeVenture?.fleet_slug?.trim();
  if (fromBar) return fromBar;
  const fromProfile = fleetProfileSlug?.trim();
  return fromProfile || null;
}

export function fleetActionTranscript(
  action: string,
  projectSlug: string | null | undefined,
  confirmed = false,
): string {
  const phrase = action.replace(/_/g, " ");
  const scoped = projectSlug ? `${phrase} on ${projectSlug}` : phrase;
  return confirmed ? `${scoped} confirm` : scoped;
}