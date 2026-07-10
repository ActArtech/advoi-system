import { PwaHomeBriefsSurface } from "@/components/PwaHomeBriefsSurface";
import { PwaHomeOnboarding } from "@/components/PwaHomeOnboarding";
import { VoiceSession } from "@/components/VoiceSession";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Stage 1 · Voice + PWA</p>
        <h1>ADVoi</h1>
        <p className={styles.lede}>Portfolio voice layer. Thin wrapper over Hermes, fleet, and memory.</p>
      </header>
      {/* Install strip + 60s morning pulse CTA — home only, no new routes */}
      <PwaHomeOnboarding />
      {/* Open briefs + review queue cards — home only; uses /api/briefs + /api/review-queue */}
      <PwaHomeBriefsSurface />
      <VoiceSession />
      <p style={{ marginTop: "1.25rem", fontSize: "0.9rem", color: "var(--muted)" }}>
        <a href="/ingest">Upload and route</a> ·{" "}
        <a href="/dashboard">Agent dashboard (run 6)</a> ·{" "}
        <a href="/voice-server">Server voice loop</a> (no WebGPU) ·{" "}
        <a href="/voice-local">Client voice loop</a> (Kokoro + Parakeet)
      </p>
    </main>
  );
}