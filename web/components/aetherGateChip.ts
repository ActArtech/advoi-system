/**
 * PWA Aether gate chip model — pure helpers for VoiceSession / dashboard.
 *
 * Fed by GET /api/aether/status (gate.verdict, gate.active_slug).
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
  /** Client-side flag when the status fetch failed. */
  error?: string | null;
  ok?: boolean;
};

export type AetherGateChipTone = "ok" | "warn" | "error" | "empty";

export type AetherGateChipModel = {
  /** False when status was never loaded or fetch failed. */
  available: boolean;
  /** Normalized gate verdict (or null when unknown / missing). */
  verdict: GateVerdict | null;
  /** Active venture slug from gate (or null). */
  activeSlug: string | null;
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

/**
 * Build the Aether gate chip presentation from /api/aether/status payload.
 * Never throws — null/partial/error inputs yield graceful empty states.
 */
export function aetherGateChipModel(
  status: AetherStatusPayload | null | undefined,
): AetherGateChipModel {
  if (status == null) {
    return {
      available: false,
      verdict: null,
      activeSlug: null,
      label: "Gate —",
      title: "Aether status unavailable",
      tone: "empty",
      found: false,
    };
  }

  if (status.error) {
    return {
      available: false,
      verdict: null,
      activeSlug: null,
      label: "Gate err",
      title: `Aether status error: ${status.error}`,
      tone: "error",
      found: false,
    };
  }

  const gate = status.gate ?? null;
  if (gate == null) {
    return {
      available: true,
      verdict: null,
      activeSlug: null,
      label: "Gate —",
      title: "Aether gate not present in status",
      tone: "empty",
      found: false,
    };
  }

  const found = Boolean(gate.found);
  const verdict = normalizeVerdict(gate.verdict);
  const activeSlug =
    gate.active_slug != null && String(gate.active_slug).trim()
      ? String(gate.active_slug).trim()
      : null;

  if (!found) {
    return {
      available: true,
      verdict: null,
      activeSlug,
      label: "Gate —",
      title: gate.path
        ? `Aether gate not found (${gate.path})`
        : "Aether gate not found",
      tone: "empty",
      found: false,
    };
  }

  const verdictPart =
    verdict && verdict !== "unknown" ? `Gate ${verdict}` : "Gate";
  const parts: string[] = [verdictPart];
  if (activeSlug) parts.push(activeSlug);
  const label = parts.join(" · ");

  const tone = toneForVerdict(verdict, found);
  const titleParts = [label];
  if (status.active_venture?.name) {
    titleParts.push(`venture ${status.active_venture.name}`);
  }
  if (gate.path) titleParts.push(gate.path);

  return {
    available: true,
    verdict,
    activeSlug,
    label,
    title: titleParts.join(" · "),
    tone,
    found: true,
  };
}
