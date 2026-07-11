"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { formatRelativeTime, type SliceRunLogEntry } from "@/lib/agents/sliceRunLog";
import { Trash2 } from "lucide-react";

type SliceRunHistoryDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entries: SliceRunLogEntry[];
  onClear: () => void;
};

export function SliceRunHistoryDrawer({
  open,
  onOpenChange,
  entries,
  onClear,
}: SliceRunHistoryDrawerProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent data-testid="slice-run-history-drawer">
        <DrawerHeader>
          <DrawerTitle>Run history</DrawerTitle>
          <DrawerDescription>
            {entries.length} run{entries.length === 1 ? "" : "s"} this session
          </DrawerDescription>
        </DrawerHeader>
        <div className="max-h-[50dvh] space-y-2 overflow-y-auto px-4">
          {entries.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No runs yet. Start a slice batch to see history here.
            </p>
          ) : (
            entries.map((entry) => (
              <Card key={entry.id} className="border-border/70">
                <CardHeader className="flex flex-row items-start justify-between space-y-0 p-3 pb-1">
                  <div className="min-w-0 space-y-0.5">
                    <CardTitle className="truncate text-sm font-medium">{entry.label}</CardTitle>
                    <p className="text-[10px] text-muted-foreground">
                      {entry.mode} · {entry.frameCount} slice{entry.frameCount === 1 ? "" : "s"} ·{" "}
                      {formatRelativeTime(entry.ts)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Badge variant="success" className="text-[10px]">
                      {entry.okCount} ok
                    </Badge>
                    {entry.failCount > 0 ? (
                      <Badge variant="warning" className="text-[10px]">
                        {entry.failCount} fail
                      </Badge>
                    ) : null}
                  </div>
                </CardHeader>
                {entry.summary ? (
                  <CardContent className="p-3 pt-0 text-xs leading-relaxed text-muted-foreground">
                    {entry.summary}
                  </CardContent>
                ) : null}
              </Card>
            ))
          )}
        </div>
        <DrawerFooter className="flex-row gap-2">
          {entries.length > 0 ? (
            <Button
              variant="secondary"
              className="flex-1"
              onClick={onClear}
              data-testid="clear-slice-run-history"
            >
              <Trash2 className="h-4 w-4" />
              Clear history
            </Button>
          ) : null}
          <DrawerClose asChild>
            <Button
              variant="secondary"
              className={entries.length > 0 ? "flex-1" : "w-full"}
            >
              Close
            </Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}