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
import type { SliceQueueItem } from "@/lib/agents/sliceRunQueue";
import { ArrowUp, Trash2, X } from "lucide-react";

type SliceQueueDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: SliceQueueItem[];
  busy: boolean;
  onRemove: (id: string) => void;
  onBump: (id: string) => void;
  onClear: () => void;
};

export function SliceQueueDrawer({
  open,
  onOpenChange,
  items,
  busy,
  onRemove,
  onBump,
  onClear,
}: SliceQueueDrawerProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent data-testid="slice-run-queue-drawer">
        <DrawerHeader>
          <DrawerTitle>Run queue</DrawerTitle>
          <DrawerDescription>
            {items.length} batch{items.length === 1 ? "" : "es"} waiting
            {busy ? " · active run in progress" : " · next starts when idle"}
          </DrawerDescription>
        </DrawerHeader>
        <div className="max-h-[50dvh] space-y-2 overflow-y-auto px-4">
          {items.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Queue empty. Start a run while busy to queue another batch.
            </p>
          ) : (
            items.map((item, index) => (
              <Card key={item.id} className="border-border/70" data-testid={`queue-item-${item.id}`}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3">
                  <div className="flex min-w-0 items-center gap-2">
                    <Badge variant="outline" className="shrink-0 text-[10px]">
                      {index + 1}
                    </Badge>
                    <CardTitle className="truncate text-sm font-medium">{item.label}</CardTitle>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {index > 0 ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        aria-label={`Bump ${item.label} to front`}
                        onClick={() => onBump(item.id)}
                        data-testid={`bump-queue-${item.id}`}
                      >
                        <ArrowUp className="h-3.5 w-3.5" />
                      </Button>
                    ) : null}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                      aria-label={`Remove ${item.label} from queue`}
                      onClick={() => onRemove(item.id)}
                      data-testid={`remove-queue-${item.id}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardHeader>
                {index === 0 && busy ? (
                  <CardContent className="p-3 pt-0 text-[10px] text-muted-foreground">
                    Runs after the current batch finishes.
                  </CardContent>
                ) : null}
              </Card>
            ))
          )}
        </div>
        <DrawerFooter className="flex-row flex-wrap gap-2">
          {items.length > 0 ? (
            <Button
              variant="secondary"
              className="flex-1 min-w-[120px]"
              onClick={onClear}
              data-testid="clear-queue-from-drawer"
            >
              <Trash2 className="h-4 w-4" />
              Clear queue
            </Button>
          ) : null}
          <DrawerClose asChild>
            <Button variant="outline" className={items.length > 0 ? "flex-1" : "w-full"}>
              Close
            </Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}