"use client";

import { Mic, FileText, LayoutGrid, Bot, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  TabProvider,
  TabPane,
  useTabNavigation,
  type AdvoiTab,
} from "@/components/shell/TabContext";

type NavItem = { tab: AdvoiTab; label: string; icon: LucideIcon };

const NAV_ITEMS: NavItem[] = [
  { tab: "voice", label: "Voice", icon: Mic },
  { tab: "agents", label: "Agents", icon: Bot },
  { tab: "briefs", label: "Briefs", icon: FileText },
  { tab: "more", label: "More", icon: LayoutGrid },
];

type AppShellProps = {
  voicePane: React.ReactNode;
  agentsPane: React.ReactNode;
  briefsPane: React.ReactNode;
  morePane: React.ReactNode;
};

export function AppShell({ voicePane, agentsPane, briefsPane, morePane }: AppShellProps) {
  return (
    <TabProvider>
      <div className="flex h-dvh flex-col overflow-hidden">
        <TabScroll
          voicePane={voicePane}
          agentsPane={agentsPane}
          briefsPane={briefsPane}
          morePane={morePane}
        />
        <BottomNav />
      </div>
    </TabProvider>
  );
}

function TabScroll({ voicePane, agentsPane, briefsPane, morePane }: AppShellProps) {
  const tabCtx = useTabNavigation();
  return (
    <div
      ref={tabCtx?.containerRef}
      data-advoi-tab-scroll
      className="flex min-h-0 flex-1 snap-x snap-mandatory overflow-x-auto overflow-y-hidden"
      style={{
        WebkitOverflowScrolling: "touch",
        scrollbarWidth: "none",
        msOverflowStyle: "none",
      }}
    >
      <TabPane>{voicePane}</TabPane>
      <TabPane>{agentsPane}</TabPane>
      <TabPane>{briefsPane}</TabPane>
      <TabPane>{morePane}</TabPane>
    </div>
  );
}

function BottomNav() {
  const tabCtx = useTabNavigation();
  if (!tabCtx) return null;

  const { activeTab, scrollProgress, scrollToTab } = tabCtx;
  const tabCount = NAV_ITEMS.length;

  return (
    <nav
      className="relative z-40 shrink-0 border-t border-border/60 bg-background/90 backdrop-blur-xl"
      role="navigation"
      aria-label="Main navigation"
      style={{
        paddingBottom: "calc(env(safe-area-inset-bottom, 0px) / 2)",
      }}
    >
      <span
        className="absolute left-0 top-0 h-0.5 rounded-full bg-primary transition-[left] duration-200"
        style={{
          width: `${100 / tabCount}%`,
          left: `${(scrollProgress / tabCount) * 100}%`,
        }}
        aria-hidden
      />
      <div className="mx-auto flex max-w-2xl items-center justify-around px-1 py-1.5">
        {NAV_ITEMS.map(({ tab, label, icon: Icon }) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => scrollToTab(tab)}
              className={cn(
                "flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 rounded-xl px-3 py-1.5 text-[11px] transition-colors",
                isActive ? "font-medium text-primary" : "text-muted-foreground",
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="h-5 w-5" strokeWidth={isActive ? 2.5 : 2} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}