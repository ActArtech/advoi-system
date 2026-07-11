"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type AdvoiTab = "voice" | "agents" | "briefs" | "more";

type TabContextValue = {
  activeTab: AdvoiTab;
  scrollProgress: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  scrollToTab: (tab: AdvoiTab) => void;
};

const TAB_ORDER: AdvoiTab[] = ["voice", "agents", "briefs", "more"];
const TAB_INDEX: Record<AdvoiTab, number> = { voice: 0, agents: 1, briefs: 2, more: 3 };

const TabContext = createContext<TabContextValue | null>(null);

export function TabProvider({ children }: { children: ReactNode }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeTab, setActiveTab] = useState<AdvoiTab>("voice");
  const [scrollProgress, setScrollProgress] = useState(0);

  const scrollToTab = useCallback((tab: AdvoiTab) => {
    const el = containerRef.current;
    if (!el) return;
    const idx = TAB_INDEX[tab];
    const width = el.clientWidth;
    el.scrollTo({ left: idx * width, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onScroll = () => {
      const width = el.clientWidth || 1;
      const progress = el.scrollLeft / width;
      setScrollProgress(progress);
      const nearest = Math.round(progress);
      const tab = TAB_ORDER[Math.min(Math.max(nearest, 0), TAB_ORDER.length - 1)];
      setActiveTab(tab);
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  const value = useMemo(
    () => ({ activeTab, scrollProgress, containerRef, scrollToTab }),
    [activeTab, scrollProgress, scrollToTab],
  );

  return <TabContext.Provider value={value}>{children}</TabContext.Provider>;
}

export function useTabNavigation() {
  return useContext(TabContext);
}

export function TabPane({ children }: { children: ReactNode }) {
  return (
    <section
      className="h-full w-full shrink-0 snap-start snap-always overflow-y-auto px-4 pb-4 pt-2"
      style={{ scrollSnapStop: "always" }}
    >
      <div className="mx-auto max-w-2xl animate-fade-in-up">{children}</div>
    </section>
  );
}