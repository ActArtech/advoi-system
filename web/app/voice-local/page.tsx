import { VoiceLoop } from "@/voice-interface/VoiceLoop";
import styles from "../page.module.css";

export default function VoiceLocalPage() {
  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Client voice</p>
        <h1>Local voice loop</h1>
        <p className={styles.lede}>
          On-device Parakeet STT and Kokoro TTS with ADVoi agent replies. Needs ~280 MB free browser
          storage. Auto-falls back to{" "}
          <a href="/voice-server">server voice</a> if disk, WebGPU, or WASM is unavailable.
        </p>
      </header>
      <VoiceLoop defaultMode="auto" />
    </main>
  );
}