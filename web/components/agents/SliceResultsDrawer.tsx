"use client";

import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import styles from "@/components/agents/agentsTheme.module.css";
import type { SliceResultRow } from "@/lib/agents/types";
import { RefreshCw } from "lucide-react";

type SliceResultsDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rows: SliceResultRow[];
  summary?: string;
  onRetryFailed?: () => void;
};

export function SliceResultsDrawer({
  open,
  onOpenChange,
  rows,
  summary,
  onRetryFailed,
}: SliceResultsDrawerProps) {
  const isFailedStatus = (status?: string) => status === "error" || status === "failed";
  const hasErrors = rows.some((row) => isFailedStatus(row.status));

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent
        className={styles.drawerSurface}
        data-testid="slice-results-drawer"
      >
        <DrawerHeader>
          <DrawerTitle>Slice results</DrawerTitle>
          <DrawerDescription>
            {rows.length} agent{rows.length === 1 ? "" : "s"} completed
          </DrawerDescription>
        </DrawerHeader>
        <div className={styles.drawerList}>
          {summary ? <p className={`${styles.drawerEmpty} !py-2 !text-left`}>{summary}</p> : null}
          {rows.map((row) => {
            const failed = isFailedStatus(row.status);
            return (
              <div key={row.frameId} className={styles.drawerItem}>
                <div className={styles.drawerItemHeader}>
                  <p className={styles.drawerItemTitle}>
                    <span className={styles.drawerItemAccent}>{row.shortLabel}</span>
                    <span className="text-slate-400"> · {row.label}</span>
                  </p>
                  <span
                    className={`${styles.resultBadge} ${
                      failed ? styles.resultBadgeFail : styles.resultBadgeOk
                    }`}
                  >
                    {row.status ?? "ok"}
                  </span>
                </div>
                {row.spokenSummary ? (
                  <p className={styles.drawerItemBody}>{row.spokenSummary}</p>
                ) : null}
              </div>
            );
          })}
        </div>
        <div className={styles.drawerFooter}>
          {hasErrors && onRetryFailed ? (
            <button
              type="button"
              className={styles.ctaSecondary}
              onClick={onRetryFailed}
              data-testid="retry-failed-slices-drawer"
            >
              <RefreshCw className="h-4 w-4" />
              Retry failed
            </button>
          ) : null}
          <DrawerClose asChild>
            <button type="button" className={styles.ctaOutline}>
              Close
            </button>
          </DrawerClose>
        </div>
      </DrawerContent>
    </Drawer>
  );
}