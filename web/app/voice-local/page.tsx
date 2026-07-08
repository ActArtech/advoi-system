import { VoiceLoop } from "@/voice-interface/VoiceLoop";
import styles from "../page.module.css";

export default function VoiceLocalPage() {
  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.eyebrow}>Client voice</p>
        <h1>Local voice loop</h1>
        <p className={styles.lede}>
          On-device Parakeet STT and Kokoro TTS with ADVoi agent replies. No LiveKit required.
        </p>
      </header>
      <VoiceLoop />
    </main>
  );
}