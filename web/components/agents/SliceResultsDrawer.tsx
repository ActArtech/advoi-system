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
import type { SliceResultRow } from "@/lib/agents/types";

type SliceResultsDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rows: SliceResultRow[];
  summary?: string;
};

export function SliceResultsDrawer({
  open,
  onOpenChange,
  rows,
  summary,
}: SliceResultsDrawerProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent data-testid="slice-results-drawer">
        <DrawerHeader>
          <DrawerTitle>Slice results</DrawerTitle>
          <DrawerDescription>
            {rows.length} agent{rows.length === 1 ? "" : "s"} completed
          </DrawerDescription>
        </DrawerHeader>
        <div className="max-h-[50dvh] space-y-2 overflow-y-auto px-4">
          {summary ? (
            <p className="text-sm text-muted-foreground">{summary}</p>
          ) : null}
          {rows.map((row) => (
            <Card key={row.frameId} className="border-border/70">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 p-3 pb-1">
                <CardTitle className="text-sm font-medium">
                  <span className="text-primary">{row.shortLabel}</span>
                  <span className="text-muted-foreground"> · {row.label}</span>
                </CardTitle>
                <Badge variant={row.status === "error" ? "warning" : "success"}>
                  {row.status ?? "ok"}
                </Badge>
              </CardHeader>
              {row.spokenSummary ? (
                <CardContent className="p-3 pt-0 text-xs leading-relaxed text-muted-foreground">
                  {row.spokenSummary}
                </CardContent>
              ) : null}
            </Card>
          ))}
        </div>
        <DrawerFooter>
          <DrawerClose asChild>
            <Button variant="secondary">Close</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}