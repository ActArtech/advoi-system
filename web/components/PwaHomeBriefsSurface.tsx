"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RUN_FRAME_EVENT } from "./pwaOnboarding";
import {
  HOME_BRIEFS_LIMIT,
  homeBriefsSurfaceModel,
  parseOpenBriefsPayload,
  parseReviewQueuePayload,
  type ReviewQueueItem,
} from "./pwaBriefsSurface";
import styles from "./PwaHomeBriefsSurface.module.css";

const apiBase =
  process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

function isAbortError(err: unknown): boolean {
  return (
    !!err &&
    typeof err === "object" &&
    "name" in err &&
    (err as { name?: string }).name === "AbortError"
  );
}

/** Shared JSON fetch for section loaders (throws on non-OK). */
async function fetchJson(
  url: string,
  signal: AbortSignal,
): Promise<unknown> {
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

/**
 * Home-only open briefs + review queue cards (no navigation to `/briefs` required).
 * Fetches existing APIs: GET /api/briefs, GET /api/review-queue.
 * Single review-queue UI on `/` (VoiceSession list removed).
 */
export function PwaHomeBriefsSurface() {
  const [openBriefs, setOpenBriefs] = useState<string[]>([]);
  const [openSource, setOpenSource] = useState<string | null>(null);
  const [openLoading, setOpenLoading] = useState(true);
  const [openError, setOpenError] = useState(false);

  const [reviewPending, setReviewPending] = useState<ReviewQueueItem[]>([]);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState(false);

  const loadGenRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const gen = ++loadGenRef.current;
    const stillCurrent = () => gen === loadGenRef.current && !ac.signal.aborted;

    setOpenLoading(true);
    setReviewLoading(true);
    setOpenError(false);
    setReviewError(false);

    fetchJson(`${apiBase}/briefs`, ac.signal)
      .then((data) => {
        if (!stillCurrent()) return;
        const parsed = parseOpenBriefsPayload(data);
        setOpenBriefs(parsed.briefs);
        setOpenSource(parsed.source);
        setOpenError(false);
      })
      .catch((err) => {
        if (isAbortError(err) || !stillCurrent()) return;
        setOpenBriefs([]);
        setOpenSource(null);
        setOpenError(true);
      })
      .finally(() => {
        if (!stillCurrent()) return;
        setOpenLoading(false);
      });

    fetchJson(`${apiBase}/review-queue`, ac.signal)
      .then((data) => {
        if (!stillCurrent()) return;
        const parsed = parseReviewQueuePayload(data);
        setReviewPending(parsed.pending);
        setReviewError(false);
      })
      .catch((err) => {
        if (isAbortError(err) || !stillCurrent()) return;
        setReviewPending([]);
        setReviewError(true);
      })
      .finally(() => {
        if (!stillCurrent()) return;
        setReviewLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => {
      clearInterval(t);
      abortRef.current?.abort();
    };
  }, [load]);

  const model = useMemo(
    () =>
      homeBriefsSurfaceModel({
        openBriefs,
        reviewPending,
        openLoading,
        openError,
        reviewLoading,
        reviewError,
        openSource,
        limit: HOME_BRIEFS_LIMIT,
      }),
    [
      openBriefs,
      reviewPending,
      openLoading,
      openError,
      reviewLoading,
      reviewError,
      openSource,
    ],
  );

  const hearOpenBriefs = useCallback(() => {
    const frameId = model.openBriefs.frameId;
    if (!frameId) return;
    window.dispatchEvent(
      new CustomEvent(RUN_FRAME_EVENT, {
        detail: { frameId, refresh: true, source: "home_briefs_surface" },
      }),
    );
    document
      .querySelector("[data-testid='ui-state-chip']")
      ?.scrollIntoView?.({ behavior: "smooth", block: "center" });
  }, [model.openBriefs.frameId]);

  const anyLoading = openLoading || reviewLoading;

  return (
    <div className={styles.wrap} data-testid="pwa-home-briefs-surface">
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>{model.eyebrow}</p>
          <h2 className={styles.heading}>{model.heading}</h2>
        </div>
        <button
          type="button"
          className={styles.refreshBtn}
          data-testid="briefs-surface-refresh"
          onClick={load}
          disabled={anyLoading}
        >
          {anyLoading ? "Loading…" : "Refresh"}
        </button>
      </div>

      <div className={styles.sections}>
        <section
          className={styles.section}
          data-testid="open-briefs-section"
          data-state={model.openBriefs.state}
          data-count={String(model.openBriefs.count)}
          aria-label="Open decision briefs"
        >
          <div className={styles.sectionHead}>
            <h3 className={styles.sectionTitle}>{model.openBriefs.title}</h3>
            <span className={styles.countBadge}>{model.openBriefs.count}</span>
          </div>
          {model.openBriefs.state === "loading" ? (
            <p className={styles.loadingState} data-testid="open-briefs-loading">
              Loading open briefs…
            </p>
          ) : null}
          {model.openBriefs.state === "error" ? (
            <p className={styles.errorState} data-testid="open-briefs-error">
              {model.openBriefs.errorLabel}
            </p>
          ) : null}
          {model.openBriefs.state === "empty" ? (
            <p className={styles.emptyState} data-testid="open-briefs-empty">
              {model.openBriefs.emptyLabel}
            </p>
          ) : null}
          {model.openBriefs.cards.length > 0 ? (
            <ul className={styles.cardList} data-testid="open-briefs-list">
              {model.openBriefs.cards.map((card) => (
                <li
                  key={card.key}
                  className={styles.card}
                  data-testid="open-brief-card"
                  data-kind={card.kind}
                >
                  <p className={styles.cardTitle}>{card.title}</p>
                  {card.meta ? (
                    <p className={styles.cardMeta} data-testid="brief-card-meta">
                      {card.meta}
                    </p>
                  ) : null}
                  <div className={styles.cardRow}>
                    <span className={`${styles.statusChip} ${styles.open_brief}`}>
                      {card.statusLabel}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {model.openBriefs.ctaLabel ? (
            <div className={styles.sectionFooter}>
              <button
                type="button"
                className={styles.ctaBtn}
                data-testid="hear-open-briefs"
                data-frame-id={model.openBriefs.frameId || ""}
                onClick={hearOpenBriefs}
              >
                {model.openBriefs.ctaLabel}
              </button>
            </div>
          ) : null}
        </section>

        <section
          className={styles.section}
          data-testid="review-queue-section"
          data-state={model.reviewQueue.state}
          data-count={String(model.reviewQueue.count)}
          aria-label="Deep review queue"
        >
          <div className={styles.sectionHead}>
            <h3 className={styles.sectionTitle}>{model.reviewQueue.title}</h3>
            <span className={styles.countBadge}>{model.reviewQueue.count}</span>
          </div>
          {model.reviewQueue.state === "loading" ? (
            <p className={styles.loadingState} data-testid="review-queue-loading">
              Loading review queue…
            </p>
          ) : null}
          {model.reviewQueue.state === "error" ? (
            <p className={styles.errorState} data-testid="review-queue-error">
              {model.reviewQueue.errorLabel}
            </p>
          ) : null}
          {model.reviewQueue.state === "empty" ? (
            <p className={styles.emptyState} data-testid="review-queue-empty">
              {model.reviewQueue.emptyLabel}
            </p>
          ) : null}
          {model.reviewQueue.cards.length > 0 ? (
            <ul className={styles.cardList} data-testid="review-queue-list">
              {model.reviewQueue.cards.map((card) => (
                <li
                  key={card.key}
                  className={styles.card}
                  data-testid="review-queue-card"
                  data-kind={card.kind}
                >
                  <p className={styles.cardTitle}>{card.title}</p>
                  {card.meta ? (
                    <p className={styles.cardMeta} data-testid="brief-card-meta">
                      {card.meta}
                    </p>
                  ) : null}
                  <div className={styles.cardRow}>
                    <span className={`${styles.statusChip} ${styles.review}`}>
                      {card.statusLabel}
                    </span>
                    {card.href ? (
                      <a
                        className={styles.cardLink}
                        href={card.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid="review-queue-open-link"
                      >
                        Open brief
                      </a>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  );
}
