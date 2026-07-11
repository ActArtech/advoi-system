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
import type { SliceQueueItem } from "@/lib/agents/sliceRunQueue";
import { ArrowDown, ArrowUp, Trash2, X } from "lucide-react";

type SliceQueueDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: SliceQueueItem[];
  busy: boolean;
  onRemove: (id: string) => void;
  onBump: (id: string) => void;
  onMove: (id: string, direction: "up" | "down") => void;
  onClear: () => void;
};

export function SliceQueueDrawer({
  open,
  onOpenChange,
  items,
  busy,
  onRemove,
  onBump,
  onMove,
  onClear,
}: SliceQueueDrawerProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent
        className={styles.drawerSurface}
        data-testid="slice-run-queue-drawer"
      >
        <DrawerHeader>
          <DrawerTitle>Run queue</DrawerTitle>
          <DrawerDescription>
            {items.length} batch{items.length === 1 ? "" : "es"} waiting
            {busy ? " · active run in progress" : " · next starts when idle"}
          </DrawerDescription>
        </DrawerHeader>
        <div className={styles.drawerList}>
          {items.length === 0 ? (
            <p className={styles.drawerEmpty}>
              Queue empty. Start a run while busy to queue another batch.
            </p>
          ) : (
            items.map((item, index) => (
              <div key={item.id} className={styles.drawerItem} data-testid={`queue-item-${item.id}`}>
                <div className={styles.drawerItemHeader}>
                  <div className="flex min-w-0 items-center gap-2">
                    <span className={styles.drawerIndex}>{index + 1}</span>
                    <p className={styles.drawerItemTitle}>{item.label}</p>
                  </div>
                  <div className={styles.drawerIconRow}>
                    {index > 0 ? (
                      <>
                        <button
                          type="button"
                          className={styles.iconBtn}
                          aria-label={`Move ${item.label} up`}
                          onClick={() => onMove(item.id, "up")}
                          data-testid={`move-queue-up-${item.id}`}
                        >
                          <ArrowUp className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          className={styles.iconBtn}
                          aria-label={`Bump ${item.label} to front`}
                          onClick={() => onBump(item.id)}
                          data-testid={`bump-queue-${item.id}`}
                        >
                          <ArrowUp className="h-3.5 w-3.5 text-sky-400" />
                        </button>
                      </>
                    ) : null}
                    {index < items.length - 1 ? (
                      <button
                        type="button"
                        className={styles.iconBtn}
                        aria-label={`Move ${item.label} down`}
                        onClick={() => onMove(item.id, "down")}
                        data-testid={`move-queue-down-${item.id}`}
                      >
                        <ArrowDown className="h-3.5 w-3.5" />
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                      aria-label={`Remove ${item.label} from queue`}
                      onClick={() => onRemove(item.id)}
                      data-testid={`remove-queue-${item.id}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {index === 0 && busy ? (
                  <p className={styles.drawerItemBody}>Runs after the current batch finishes.</p>
                ) : null}
              </div>
            ))
          )}
        </div>
        <div className={styles.drawerFooter}>
          {items.length > 0 ? (
            <button
              type="button"
              className={styles.ctaSecondary}
              onClick={onClear}
              data-testid="clear-queue-from-drawer"
            >
              <Trash2 className="h-4 w-4" />
              Clear queue
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