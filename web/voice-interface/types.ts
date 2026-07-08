export type VoiceId =
  | "af_heart"
  | "af_sky"
  | "am_puck"
  | "bf_emma"
  | "af_bella"
  | "am_michael";

export const WARM_VOICES: { id: VoiceId; label: string }[] = [
  { id: "af_heart", label: "Heart (warm)" },
  { id: "af_sky", label: "Sky (calm)" },
  { id: "am_puck", label: "Puck (friendly)" },
  { id: "bf_emma", label: "Emma (British)" },
  { id: "af_bella", label: "Bella (expressive)" },
  { id: "am_michael", label: "Michael (steady)" },
];

export type TranscriptHandler = (text: string, isFinal: boolean) => void;