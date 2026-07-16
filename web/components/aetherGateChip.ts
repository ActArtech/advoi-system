/**
 * PWA Aether gate chip model — pure helpers for VoiceSession / dashboard.
 *
 * Fed by GET /api/aether/status (gate.verdict, gate.active_slug) plus optional
 * project-bar working venture so Governance vs Working project stay distinct.
 * Keep Python mirror in tests/test_aether_gate_chip.py in sync.
 */

export type GateVerdict = "pass" | "hold" | "fail" | "unknown" | string;

export type AetherGatePayload = {
  found?: boolean;
  verdict?: GateVerdict | null;
  active_slug?: string | null;
  path?: string | null;
};

export type AetherStatusPayload = {
  gate?: AetherGatePayload | null;
  active_venture?: { id?: string; name?: string } | null;
  active_venture_resolved?: boolean;
  execution_context?: {
    venture_id?: string | null;
    fleet_slug?: string | null;
    source?: string | null;
  } | null;
  /** Client-side flag when the status fetch failed. */
  error?: string | null;
  ok?: boolean;
};

/** Project bar / session working venture (may differ from gate active slug). */
export type AetherGateChipOptions = {
  workingVentureId?: string | null;
  workingVentureName?: string | null;
  workingFleetSlug?: string | null;
};

export type AetherGateChipTone = "ok" | "warn" | "error" | "empty";

export type AetherGateChipModel = {
  /** False when status was never loaded or fetch failed. */
  available: boolean;
  /** Normalized gate verdict (or null when unknown / missing). */
  verdict: GateVerdict | null;
  /** Active venture slug from gate (or null). */
  activeSlug: string | null;
  /** Working project fleet slug when provided / from execution_context. */
  workingSlug: string | null;
  /** Short chip label for the status row. */
  label: string;
  /** Hover / accessibility title. */
  title: string;
  tone: AetherGateChipTone;
  found: boolean;
};

function normalizeVerdict(raw: unknown): GateVerdict | null {
  if (raw == null) return null;
  const v = String(raw).trim().toLowerCase();
  if (!v) return null;
  if (v === "pass" || v === "go") return "pass";
  if (v === "hold") return "hold";
  if (v === "fail" || v === "blocked" || v === "no-go" || v === "no go") return "fail";
  if (v === "unknown") return "unknown";
  return v;
}

function toneForVerdict(verdict: GateVerdict | null, found: boolean): AetherGateChipTone {
  if (!found || verdict == null || verdict === "unknown") return "empty";
  if (verdict === "pass") return "ok";
  if (verdict === "hold") return "warn";
  if (verdict === "fail") return "error";
  return "empty";
}

function shortSlug(slug: string | null | undefined): string | null {
  if (slug == null) return null;
  const s = String(slug).trim();
  return s || null;
}

function resolveWorkingSlug(
  status: AetherStatusPayload,
  options?: AetherGateChipOptions,
): { slug: string | null; name: string | null } {
  const fromBar = shortSlug(options?.workingFleetSlug) || shortSlug(options?.workingVentureId);
  if (fromBar) {
    return {
      slug: fromBar,
      name: options?.workingVentureName?.trim() || null,
    };
  }
  const ecr = status.execution_context;
  if (ecr?.source === "session") {
    const slug = shortSlug(ecr.fleet_slug) || shortSlug(ecr.venture_id);
    if (slug) return { slug, name: null };
  }
  return { slug: null, name: null };
}

function emptyModel(
  partial: Partial<AetherGateChipModel> & Pick<AetherGateChipModel, "label" | "title" | "tone">,
): AetherGateChipModel {
  return {
    available: partial.available ?? false,
    verdict: partial.verdict ?? null,
    activeSlug: partial.activeSlug ?? null,
    workingSlug: partial.workingSlug ?? null,
    label: partial.label,
    title: partial.title,
    tone: partial.tone,
    found: partial.found ?? false,
  };
}

/**
 * Build the Aether gate chip presentation from /api/aether/status payload.
 * Never throws — null/partial/error inputs yield graceful empty states.
 *
 * Label uses "Gov" for governance gate (sole AETHER active venture) and
 * "Work" when the project bar session points at a different venture.
 */
export function aetherGateChipModel(
  status: AetherStatusPayload | null | undefined,
  options?: AetherGateChipOptions,
): AetherGateChipModel {
  if (status == null) {
    return emptyModel({
      available: false,
      label: "Gate —",
      title: "Aether status unavailable",
      tone: "empty",
      found: false,
    });
  }

  if (status.error) {
    return emptyModel({
      available: false,
      label: "Gate err",
      title: `Aether status error: ${status.error}`,
      tone: "error",
      found: false,
    });
  }

  const gate = status.gate ?? null;
  const working = resolveWorkingSlug(status, options);

  if (gate == null) {
    return emptyModel({
      available: true,
      workingSlug: working.slug,
      label: "Gate —",
      title: "Aether gate not present in status",
      tone: "empty",
      found: false,
    });
  }

  const found = Boolean(gate.found);
  const verdict = normalizeVerdict(gate.verdict);
  const activeSlug = shortSlug(gate.active_slug);

  if (!found) {
    return emptyModel({
      available: true,
      activeSlug,
      workingSlug: working.slug,
      label: "Gate —",
      title: gate.path
        ? `Aether gate not found (${gate.path})`
        : "Aether gate not found",
      tone: "empty",
      found: false,
    });
  }

  const verdictWord =
    verdict && verdict !== "unknown" ? String(verdict) : null;
  // Compact chip: "Gov pass · gem-dev-shop" (governance truth).
  let label =
    verdictWord && activeSlug
      ? `Gov ${verdictWord} · ${activeSlug}`
      : verdictWord
        ? `Gov ${verdictWord}`
        : activeSlug
          ? `Gov · ${activeSlug}`
          : "Gov";

  // When project bar differs from gate, append working project so switch is not "broken".
  const workSlug = working.slug;
  const gateKey = (activeSlug || "").toLowerCase();
  const workKey = (workSlug || "").toLowerCase();
  const diverged =
    Boolean(workSlug) &&
    Boolean(gateKey) &&
    workKey !== gateKey &&
    !workKey.includes(gateKey) &&
    !gateKey.includes(workKey);

  if (diverged && workSlug) {
    label = `${label} · Work ${workSlug}`;
  }

  const tone = toneForVerdict(verdict, found);
  const titleParts: string[] = [];
  titleParts.push(
    activeSlug
      ? `Governance: ${verdictWord ?? "gate"} · ${activeSlug}`
      : `Governance: ${verdictWord ?? "gate"}`,
  );
  if (workSlug) {
    const workName = working.name?.trim();
    titleParts.push(
      workName
        ? `Working project: ${workName} (${workSlug})`
        : `Working project: ${workSlug}`,
    );
  } else if (status.active_venture?.name && !diverged) {
    titleParts.push(`venture ${status.active_venture.name}`);
  }
  if (gate.path) titleParts.push(gate.path);

  return {
    available: true,
    verdict,
    activeSlug,
    workingSlug: workSlug,
    label,
    title: titleParts.join(" | "),
    tone,
    found: true,
  };
}
