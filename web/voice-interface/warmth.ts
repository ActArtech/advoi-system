export function stripEmDash(text: string): string {
  return text.replace(/\u2014/g, ", ").replace(/\u2013/g, ", ").replace(/  +/g, " ").trim();
}

export function warmTextForTTS(text: string): string {
  let out = stripEmDash(text);
  out = out.replace(/\. /g, ". ... ");
  return out;
}

// Keep in sync with advoi.routing.intent._CONFIRM_WORDS / is_confirm_phrase.
// Prefer multi-word forms before bare "go" so "go ahead" still matches cleanly.
const CONFIRM_RE =
  /^(yes|yeah|yep|yup|confirm|confirmed|go ahead|go on|let'?s go|go|do it|ship it|sure|okay|ok|proceed|approved)\b/i;

export function isConfirmPhrase(transcript: string): boolean {
  return CONFIRM_RE.test((transcript || "").trim());
}

export function mirrorPhrases(transcript: string, max = 2): string[] {
  const words = transcript
    .toLowerCase()
    .replace(/[^\w\s']/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 3);
  const seen = new Set<string>();
  const picks: string[] = [];
  for (const w of words) {
    if (seen.has(w)) continue;
    seen.add(w);
    picks.push(w);
    if (picks.length >= max) break;
  }
  return picks;
}