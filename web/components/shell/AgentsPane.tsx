"use client";

import { AgentsOrchestrator } from "@/components/agents/AgentsOrchestrator";
import styles from "@/components/agents/agentsTheme.module.css";

export function AgentsPane() {
  return (
    <div className="space-y-4 pb-6" data-testid="agents-pane">
      <header className={styles.hero}>
        <div className={styles.heroBadges}>
          <span className={styles.heroBadgePrimary}>Multi-agent v2</span>
          <span className={styles.heroBadgeOutline}>Queue · Chains · Squads</span>
        </div>
        <h2 className={styles.heroTitle}>Agent orchestrator</h2>
        <p className={styles.heroDesc}>
          Executive slate control layer. Tap slices (keys 1-6), run preset chains, queue batches
          while busy, and sync voice CTAs from the Voice tab.
        </p>
      </header>
      <AgentsOrchestrator />
    </div>
  );
}