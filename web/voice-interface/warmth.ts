export function stripEmDash(text: string): string {
  return text.replace(/\u2014/g, ", ").replace(/\u2013/g, ", ").replace(/  +/g, " ").trim();
}

export function warmTextForTTS(text: string): string {
  let out = stripEmDash(text);
  out = out.replace(/\. /g, ". ... ");
  return out;
}

const CONFIRM_RE =
  /^(yes|yeah|yep|confirm|confirmed|go ahead|do it|sure|okay|ok|proceed|approved)\b/i;

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