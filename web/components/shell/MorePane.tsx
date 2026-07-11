"use client";

import Link from "next/link";
import {
  Upload,
  LayoutDashboard,
  Radio,
  Smartphone,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";

const LINKS = [
  {
    href: "/ingest",
    label: "Upload and route",
    description: "Ingestion triage and fleet dispatch",
    icon: Upload,
  },
  {
    href: "/dashboard",
    label: "Agent dashboard",
    description: "Run 6 agents and squad dispatch",
    icon: LayoutDashboard,
  },
  {
    href: "/voice-server",
    label: "Server voice loop",
    description: "Path C — no WebGPU required",
    icon: Radio,
  },
  {
    href: "/voice-local",
    label: "Client voice loop",
    description: "Kokoro + Parakeet in browser",
    icon: Smartphone,
  },
] as const;

export function MorePane() {
  return (
    <div className="space-y-4 pb-6">
      <header className="space-y-1 pt-2">
        <Badge variant="secondary">Portfolio tools</Badge>
        <h2 className="text-xl font-semibold tracking-tight">More</h2>
        <p className="text-sm text-muted-foreground">
          Ingestion, dashboard, and alternate voice paths.
        </p>
      </header>

      <div className="stagger-children space-y-3">
        {LINKS.map(({ href, label, description, icon: Icon }) => (
          <Link key={href} href={href} className="block">
            <Card className="transition-colors hover:border-primary/40 hover:bg-accent/30">
              <CardHeader className="flex flex-row items-center gap-3 space-y-0 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-base">{label}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      <Drawer>
        <DrawerTrigger asChild>
          <Button variant="outline" className="w-full" data-testid="more-quick-actions">
            Quick actions
          </Button>
        </DrawerTrigger>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Quick actions</DrawerTitle>
            <DrawerDescription>
              Swipe down or tap outside to close. Fleet and operator actions live on the Voice tab.
            </DrawerDescription>
          </DrawerHeader>
          <CardContent className="space-y-2 px-4 pb-2 text-sm text-muted-foreground">
            <p>Use the Voice tab for Connect, frames A-F, and operator bar.</p>
            <p>Say &quot;what can you do&quot; or tap Run all 6 after connecting.</p>
          </CardContent>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button variant="secondary">Close</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </div>
  );
}