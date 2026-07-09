import { VoiceLoop } from "@/voice-interface/VoiceLoop";
import styles from "../page.module.css";

export default function VoiceServerPage() {
  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Server voice</p>
        <h1>Server voice loop</h1>
        <p className={styles.lede}>
          Browser speech recognition plus server-side TTS. No Kokoro, Parakeet, or WebGPU required.
        </p>
      </header>
      <VoiceLoop defaultMode="server" />
    </main>
  );
}