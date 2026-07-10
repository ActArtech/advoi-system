/**
 * PWA SLA latency chip model — pure helpers for VoiceSession.
 *
 * Fed by GET /api/diagnostics/latency (frame_run_ms, run_six_ms, sla_ok).
 * Keep Python mirror in tests/test_latency_chip.py in sync.
 */

export type LatencyTimings = {
  frame_run_ms?: number | null;
  run_six_ms?: number | null;
  api_voice_path_ms?: number | null;
};

export type LatencyDiagnostics = {
  ok?: boolean;
  sla_ok?: boolean | null;
  sla_target_ms?: number | null;
  timings_ms?: LatencyTimings | null;
  /** Present when the probe itself failed hard (optional client-side flag). */
  error?: string | null;
};

export type LatencyChipTone = "ok" | "warn" | "empty" | "error";

export type LatencyChipModel = {
  /** False when diagnostics were never loaded or fetch failed. */
  available: boolean;
  /** Null when SLA cannot be evaluated. */
  slaOk: boolean | null;
  /** Short chip label for the status row. */
  label: string;
  /** Hover / accessibility title. */
  title: string;
  tone: LatencyChipTone;
  frameRunMs: number | null;
  runSixMs: number | null;
};

function formatMs(ms: number | null | undefined): string | null {
  if (ms == null || Number.isNaN(Number(ms))) return null;
  const n = Number(ms);
  if (n < 10) return `${n.toFixed(1)}ms`;
  return `${Math.round(n)}ms`;
}

/**
 * Build the SLA chip presentation from a diagnostics payload.
 * Never throws — null/partial/error inputs yield graceful empty states.
 */
export function latencyChipModel(
  diag: LatencyDiagnostics | null | undefined,
): LatencyChipModel {
  if (diag == null) {
    return {
      available: false,
      slaOk: null,
      label: "SLA —",
      title: "Latency diagnostics unavailable",
      tone: "empty",
      frameRunMs: null,
      runSixMs: null,
    };
  }

  if (diag.error) {
    return {
      available: false,
      slaOk: null,
      label: "SLA err",
      title: `Latency diagnostics error: ${diag.error}`,
      tone: "error",
      frameRunMs: null,
      runSixMs: null,
    };
  }

  const timings = diag.timings_ms ?? {};
  const frameRunMs =
    timings.frame_run_ms != null && !Number.isNaN(Number(timings.frame_run_ms))
      ? Number(timings.frame_run_ms)
      : null;
  const runSixMs =
    timings.run_six_ms != null && !Number.isNaN(Number(timings.run_six_ms))
      ? Number(timings.run_six_ms)
      : null;

  const parts: string[] = [];
  const frameLabel = formatMs(frameRunMs);
  const sixLabel = formatMs(runSixMs);
  if (frameLabel) parts.push(`frame ${frameLabel}`);
  if (sixLabel) parts.push(`six ${sixLabel}`);

  const hasTimings = parts.length > 0;
  const slaOk = typeof diag.sla_ok === "boolean" ? diag.sla_ok : null;

  let label: string;
  let tone: LatencyChipTone;
  let title: string;

  if (!hasTimings && slaOk == null) {
    label = "SLA —";
    tone = diag.ok === false ? "error" : "empty";
    title =
      diag.ok === false
        ? "Latency probe incomplete"
        : "Latency timings not yet available";
  } else {
    const slaPart =
      slaOk === true ? "SLA ok" : slaOk === false ? "SLA miss" : "SLA";
    label = parts.length > 0 ? `${slaPart} · ${parts.join(" · ")}` : slaPart;
    tone = slaOk === true ? "ok" : slaOk === false ? "warn" : "empty";
    const target =
      diag.sla_target_ms != null ? ` (target ${diag.sla_target_ms}ms)` : "";
    title = `${label}${target}`;
  }

  return {
    available: true,
    slaOk,
    label,
    title,
    tone,
    frameRunMs,
    runSixMs,
  };
}
