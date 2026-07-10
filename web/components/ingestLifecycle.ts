/**
 * Ingestion UI lifecycle helpers — pure model for /ingest.
 *
 * Mirrors API contract in tests/test_ingestion_lifecycle.py:
 *   uploaded → triaged → needs_review → approved → dispatched
 * Dispatch only from approved; no auto-dispatch on upload.
 *
 * Keep Python mirror in tests/test_ingest_ui_lifecycle.py in sync.
 */

export type IngestStatus =
  | "uploaded"
  | "triaged"
  | "needs_review"
  | "routed"
  | "approved"
  | "dispatched"
  | "failed"
  | string;

export type LifecycleActionId = "triage" | "needs_review" | "approve" | "dispatch_dev";

export type LifecycleAction = {
  id: LifecycleActionId;
  /** Button label */
  label: string;
  /** Path suffix after /api/ingestion/items/{id}/ */
  path: string;
  /** HTTP method (always POST for lifecycle) */
  method: "POST";
  /** JSON body when needed (dispatch-dev) */
  body?: Record<string, unknown>;
};

export type BadgeTone = "neutral" | "progress" | "review" | "ready" | "done" | "error";

/** Happy-path order (documentation + tests). */
export const HAPPY_PATH: readonly string[] = [
  "uploaded",
  "triaged",
  "needs_review",
  "approved",
  "dispatched",
];

/**
 * Available primary actions for a queue item status.
 * Legacy `routed` can move to needs_review or approved (API ALLOWED_TRANSITIONS).
 */
export function actionsForStatus(status: IngestStatus): LifecycleAction[] {
  switch (status) {
    case "uploaded":
      return [
        {
          id: "triage",
          label: "Triage",
          path: "triage",
          method: "POST",
        },
      ];
    case "triaged":
      return [
        {
          id: "needs_review",
          label: "Needs review",
          path: "needs-review",
          method: "POST",
        },
      ];
    case "needs_review":
      return [
        {
          id: "approve",
          label: "Approve",
          path: "approve",
          method: "POST",
        },
      ];
    case "routed":
      // Legacy pre-lifecycle status — either advance path is valid.
      return [
        {
          id: "needs_review",
          label: "Needs review",
          path: "needs-review",
          method: "POST",
        },
        {
          id: "approve",
          label: "Approve",
          path: "approve",
          method: "POST",
        },
      ];
    case "approved":
      return [
        {
          id: "dispatch_dev",
          label: "Dispatch to FirstMate",
          path: "dispatch-dev",
          method: "POST",
          body: { confirmed: true, mode: "work" },
        },
      ];
    case "dispatched":
    case "failed":
    default:
      return [];
  }
}

/** Build full API URL for a lifecycle action. */
export function actionUrl(apiBase: string, itemId: string, action: LifecycleAction): string {
  const base = apiBase.replace(/\/$/, "");
  return `${base}/ingestion/items/${encodeURIComponent(itemId)}/${action.path}`;
}

/** Badge tone for status chip styling. */
export function statusBadgeTone(status: IngestStatus): BadgeTone {
  switch (status) {
    case "uploaded":
      return "neutral";
    case "triaged":
    case "routed":
      return "progress";
    case "needs_review":
      return "review";
    case "approved":
      return "ready";
    case "dispatched":
      return "done";
    case "failed":
      return "error";
    default:
      return "neutral";
  }
}

export type ParsedApiError = {
  message: string;
  /** HTTP status when known */
  httpStatus: number | null;
  /** Ontology / FastAPI code when present (e.g. UNKNOWN_VENTURE_ID) */
  code: string | null;
  /** True for ontology 422 or item.status === failed */
  isError: boolean;
};

/**
 * Parse API error bodies for upload + lifecycle actions.
 * Handles: 422 ontology {detail, code}, 409 transition, {ok:false,error}, failed items.
 */
export function parseApiError(
  httpStatus: number | null,
  body: unknown,
): ParsedApiError {
  const empty: ParsedApiError = {
    message: "Request failed.",
    httpStatus,
    code: null,
    isError: true,
  };
  if (body == null || typeof body !== "object") {
    if (httpStatus === 422) {
      return { ...empty, message: "Ontology validation failed (422)." };
    }
    if (httpStatus === 409) {
      return { ...empty, message: "Invalid lifecycle transition (409)." };
    }
    return empty;
  }
  const b = body as Record<string, unknown>;
  const code = typeof b.code === "string" ? b.code : null;
  let message: string | null = null;

  if (typeof b.detail === "string" && b.detail.trim()) {
    message = b.detail;
  } else if (Array.isArray(b.detail) && b.detail.length) {
    // FastAPI validation error list
    const parts = b.detail.map((d) => {
      if (d && typeof d === "object" && "msg" in d) {
        return String((d as { msg: unknown }).msg);
      }
      return String(d);
    });
    message = parts.join("; ");
  } else if (typeof b.error === "string" && b.error.trim()) {
    message = b.error;
  } else if (typeof b.spoken === "string" && b.spoken.trim()) {
    message = b.spoken;
  } else if (typeof b.status === "string" && b.ok === false) {
    message = String(b.status);
  }

  if (httpStatus === 422) {
    const prefix = code ? `Ontology 422 (${code})` : "Ontology 422";
    return {
      message: message ? `${prefix}: ${message}` : `${prefix}.`,
      httpStatus,
      code,
      isError: true,
    };
  }
  if (httpStatus === 409) {
    return {
      message: message || "Invalid lifecycle transition (409).",
      httpStatus,
      code,
      isError: true,
    };
  }
  if (b.ok === false) {
    return {
      message: message || "Request failed.",
      httpStatus,
      code,
      isError: true,
    };
  }
  // Failed item in payload
  const item = b.item as Record<string, unknown> | undefined;
  if (item && item.status === "failed") {
    const err =
      (typeof item.error === "string" && item.error) ||
      message ||
      "Item marked failed.";
    return { message: err, httpStatus, code, isError: true };
  }
  if (message) {
    return { message, httpStatus, code, isError: httpStatus != null && httpStatus >= 400 };
  }
  if (httpStatus != null && httpStatus >= 400) {
    return empty;
  }
  return { message: "", httpStatus, code, isError: false };
}

/** Human-readable success line after a lifecycle step. */
export function lifecycleSuccessMessage(
  actionId: LifecycleActionId,
  item: { status?: string; project_slug?: string | null; filename?: string },
): string {
  const name = item.filename || "item";
  const st = item.status || "?";
  switch (actionId) {
    case "triage":
      return `Triaged ${name} → ${st}.`;
    case "needs_review":
      return `Marked ${name} needs review.`;
    case "approve":
      return `Approved ${name}. Ready to dispatch.`;
    case "dispatch_dev":
      return `Dispatched ${name} to FirstMate (${item.project_slug || "project"}).`;
    default:
      return `Updated ${name} → ${st}.`;
  }
}
