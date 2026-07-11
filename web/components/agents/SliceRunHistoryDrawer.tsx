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
import { formatRelativeTime, type SliceRunLogEntry } from "@/lib/agents/sliceRunLog";
import { Download, RefreshCw, Trash2, Upload } from "lucide-react";

type SliceRunHistoryDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entries: SliceRunLogEntry[];
  onClear: () => void;
  onRerun?: (entry: SliceRunLogEntry) => void;
  rerunDisabled?: boolean;
  onExport?: () => void;
  onImport?: () => void;
};

export function SliceRunHistoryDrawer({
  open,
  onOpenChange,
  entries,
  onClear,
  onRerun,
  rerunDisabled,
  onExport,
  onImport,
}: SliceRunHistoryDrawerProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent
        className={styles.drawerSurface}
        data-testid="slice-run-history-drawer"
      >
        <DrawerHeader>
          <DrawerTitle>Run history</DrawerTitle>
          <DrawerDescription>
            {entries.length} run{entries.length === 1 ? "" : "s"} this session
          </DrawerDescription>
        </DrawerHeader>
        <div className={styles.drawerList}>
          {entries.length === 0 ? (
            <p className={styles.drawerEmpty}>
              No runs yet. Start a slice batch to see history here.
            </p>
          ) : (
            entries.map((entry) => (
              <div key={entry.id} className={styles.drawerItem}>
                <div className={styles.drawerItemHeader}>
                  <div className="min-w-0">
                    <p className={styles.drawerItemTitle}>{entry.label}</p>
                    <p className={styles.drawerItemMeta}>
                      {entry.mode} · {entry.frameCount} slice{entry.frameCount === 1 ? "" : "s"} ·{" "}
                      {formatRelativeTime(entry.ts)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <span className={`${styles.resultBadge} ${styles.resultBadgeOk}`}>
                      {entry.okCount} ok
                    </span>
                    {entry.failCount > 0 ? (
                      <span className={`${styles.resultBadge} ${styles.resultBadgeWarn}`}>
                        {entry.failCount} fail
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className={styles.drawerItemBody}>
                  {entry.summary ? <p className="m-0">{entry.summary}</p> : null}
                  {onRerun && entry.frameIds && entry.frameIds.length > 0 ? (
                    <button
                      type="button"
                      className={`${styles.ctaOutline} mt-2 !min-w-0 !flex-none`}
                      disabled={rerunDisabled}
                      onClick={() => onRerun(entry)}
                      data-testid={`rerun-history-${entry.id}`}
                    >
                      <RefreshCw className="h-3 w-3" />
                      Re-run
                    </button>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
        <div className={styles.drawerFooter}>
          {onExport ? (
            <button
              type="button"
              className={styles.ctaOutline}
              onClick={onExport}
              data-testid="export-slice-run-history"
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          ) : null}
          {onImport ? (
            <button
              type="button"
              className={styles.ctaOutline}
              onClick={onImport}
              data-testid="import-slice-run-history"
            >
              <Upload className="h-4 w-4" />
              Import
            </button>
          ) : null}
          {entries.length > 0 ? (
            <button
              type="button"
              className={styles.ctaSecondary}
              onClick={onClear}
              data-testid="clear-slice-run-history"
            >
              <Trash2 className="h-4 w-4" />
              Clear
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