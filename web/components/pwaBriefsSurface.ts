/**
 * PWA home briefs surface — pure helpers for open briefs + review queue cards.
 *
 * Surfaces existing data on `/` without navigating to `/briefs`:
 * - GET /api/briefs (open decision briefs)
 * - GET /api/review-queue (deep review pending)
 *
 * Keep Python mirror in tests/test_pwa_briefs_surface.py in sync.
 */

/** Max cards per section on the home surface. */
export const HOME_BRIEFS_LIMIT = 5;

/** Frame id for “Hear open briefs” CTA. */
export const OPEN_BRIEFS_FRAME_ID = "open_briefs";

export type OpenBriefItem = {
  title: string;
  /** Optional stable id when API provides one (title-only today). */
  id?: string | number;
};

export type ReviewQueueItem = {
  queue_id: number;
  title: string;
  status: string;
  brief_url?: string;
  source_frame?: string;
  created_at?: string;
};

export type FetchState = "idle" | "loading" | "ok" | "error" | "empty";

export type BriefCardModel = {
  key: string;
  title: string;
  kind: "open_brief" | "review";
  statusLabel: string;
  href: string | null;
  meta: string | null;
};

export type SectionModel = {
  id: "open_briefs" | "review_queue";
  title: string;
  state: FetchState;
  count: number;
  emptyLabel: string;
  errorLabel: string;
  cards: BriefCardModel[];
  /** Optional footer / CTA label. */
  ctaLabel: string | null;
  frameId: string | null;
};

export type HomeBriefsSurfaceModel = {
  openBriefs: SectionModel;
  reviewQueue: SectionModel;
  /** True when either section has cards to show. */
  hasAnyCards: boolean;
  /** Overall eyebrow for the surface. */
  eyebrow: string;
  heading: string;
};

/**
 * Normalize open-briefs API payload into title strings.
 */
export function parseOpenBriefsPayload(data: unknown): {
  briefs: string[];
  source: string | null;
  count: number;
} {
  if (data == null || typeof data !== "object") {
    return { briefs: [], source: null, count: 0 };
  }
  const raw = data as {
    briefs?: unknown;
    count?: unknown;
    source?: unknown;
  };
  const list = Array.isArray(raw.briefs) ? raw.briefs : [];
  const briefs: string[] = [];
  for (const item of list) {
    if (typeof item === "string") {
      const t = item.trim();
      if (t) briefs.push(t);
    } else if (item && typeof item === "object" && "title" in item) {
      const t = String((item as { title: unknown }).title || "").trim();
      if (t) briefs.push(t);
    }
  }
  const count =
    typeof raw.count === "number" && Number.isFinite(raw.count)
      ? raw.count
      : briefs.length;
  const source =
    raw.source != null && String(raw.source).trim()
      ? String(raw.source).trim()
      : null;
  return { briefs, source, count };
}

/**
 * Normalize review-queue API payload.
 */
export function parseReviewQueuePayload(data: unknown): {
  pending: ReviewQueueItem[];
  count: number;
} {
  if (data == null || typeof data !== "object") {
    return { pending: [], count: 0 };
  }
  const raw = data as { pending?: unknown; count?: unknown };
  const list = Array.isArray(raw.pending) ? raw.pending : [];
  const pending: ReviewQueueItem[] = [];
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const queueId = Number(row.queue_id);
    const title = String(row.title || "").trim();
    if (!Number.isFinite(queueId) || !title) continue;
    pending.push({
      queue_id: queueId,
      title,
      status: String(row.status || "pending"),
      brief_url:
        row.brief_url != null && String(row.brief_url).trim()
          ? String(row.brief_url).trim()
          : undefined,
      source_frame:
        row.source_frame != null ? String(row.source_frame) : undefined,
      created_at: row.created_at != null ? String(row.created_at) : undefined,
    });
  }
  const count =
    typeof raw.count === "number" && Number.isFinite(raw.count)
      ? raw.count
      : pending.length;
  return { pending, count };
}

/**
 * Build open-briefs section presentation (pure; safe for unit tests + SSR).
 */
export function openBriefsSectionModel(input: {
  briefs: string[];
  loading?: boolean;
  error?: boolean;
  source?: string | null;
  limit?: number;
}): SectionModel {
  const limit = input.limit ?? HOME_BRIEFS_LIMIT;
  if (input.loading) {
    return {
      id: "open_briefs",
      title: "Open briefs",
      state: "loading",
      count: 0,
      emptyLabel: "No open briefs in memory.",
      errorLabel: "Could not load open briefs.",
      cards: [],
      ctaLabel: "Hear open briefs",
      frameId: OPEN_BRIEFS_FRAME_ID,
    };
  }
  if (input.error) {
    return {
      id: "open_briefs",
      title: "Open briefs",
      state: "error",
      count: 0,
      emptyLabel: "No open briefs in memory.",
      errorLabel: "Could not load open briefs.",
      cards: [],
      ctaLabel: "Hear open briefs",
      frameId: OPEN_BRIEFS_FRAME_ID,
    };
  }
  const titles = (input.briefs || []).map((t) => t.trim()).filter(Boolean);
  const sliced = titles.slice(0, limit);
  const cards: BriefCardModel[] = sliced.map((title, i) => ({
    key: `open-${i}-${title.slice(0, 24)}`,
    title,
    kind: "open_brief",
    statusLabel: "open",
    href: null,
    meta: input.source ? `source: ${input.source}` : null,
  }));
  return {
    id: "open_briefs",
    title: "Open briefs",
    state: cards.length === 0 ? "empty" : "ok",
    count: titles.length,
    emptyLabel: "No open briefs in memory.",
    errorLabel: "Could not load open briefs.",
    cards,
    ctaLabel: "Hear open briefs",
    frameId: OPEN_BRIEFS_FRAME_ID,
  };
}

/**
 * Build review-queue section presentation.
 */
export function reviewQueueSectionModel(input: {
  pending: ReviewQueueItem[];
  loading?: boolean;
  error?: boolean;
  limit?: number;
}): SectionModel {
  const limit = input.limit ?? HOME_BRIEFS_LIMIT;
  if (input.loading) {
    return {
      id: "review_queue",
      title: "Review queue",
      state: "loading",
      count: 0,
      emptyLabel: "Review queue is clear.",
      errorLabel: "Could not load review queue.",
      cards: [],
      ctaLabel: null,
      frameId: null,
    };
  }
  if (input.error) {
    return {
      id: "review_queue",
      title: "Review queue",
      state: "error",
      count: 0,
      emptyLabel: "Review queue is clear.",
      errorLabel: "Could not load review queue.",
      cards: [],
      ctaLabel: null,
      frameId: null,
    };
  }
  const items = input.pending || [];
  const sliced = items.slice(0, limit);
  const cards: BriefCardModel[] = sliced.map((item) => {
    const href =
      item.brief_url && item.brief_url.trim()
        ? item.brief_url.trim()
        : `/briefs/${item.queue_id}`;
    return {
      key: `review-${item.queue_id}`,
      title: item.title,
      kind: "review",
      statusLabel: item.status || "pending",
      href,
      meta: item.created_at ? `queued ${item.created_at}` : null,
    };
  });
  return {
    id: "review_queue",
    title: "Review queue",
    state: cards.length === 0 ? "empty" : "ok",
    count: items.length,
    emptyLabel: "Review queue is clear.",
    errorLabel: "Could not load review queue.",
    cards,
    ctaLabel: null,
    frameId: null,
  };
}

/**
 * Compose full home surface model from mock or live data.
 */
export function homeBriefsSurfaceModel(input: {
  openBriefs: string[];
  reviewPending: ReviewQueueItem[];
  openLoading?: boolean;
  openError?: boolean;
  reviewLoading?: boolean;
  reviewError?: boolean;
  openSource?: string | null;
  limit?: number;
}): HomeBriefsSurfaceModel {
  const openBriefs = openBriefsSectionModel({
    briefs: input.openBriefs,
    loading: input.openLoading,
    error: input.openError,
    source: input.openSource,
    limit: input.limit,
  });
  const reviewQueue = reviewQueueSectionModel({
    pending: input.reviewPending,
    loading: input.reviewLoading,
    error: input.reviewError,
    limit: input.limit,
  });
  return {
    openBriefs,
    reviewQueue,
    hasAnyCards: openBriefs.cards.length > 0 || reviewQueue.cards.length > 0,
    eyebrow: "Decisions · home",
    heading: "Open briefs & review",
  };
}
