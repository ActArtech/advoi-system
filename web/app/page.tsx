import { VoiceSession } from "@/components/VoiceSession";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Stage 1 · Voice + PWA</p>
        <h1>ADVoi</h1>
        <p className={styles.lede}>Portfolio voice layer — thin wrapper over Hermes, fleet, and memory.</p>
      </header>
      <VoiceSession />
    </main>
  );
}