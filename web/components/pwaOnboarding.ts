/**
 * PWA home onboarding — pure helpers for install strip + 60s morning pulse CTA.
 *
 * Product voice (PORTFOLIO-SYSTEM-MOAT Pattern F):
 * ADVoi is the third leg of the daily loop — a 60-second portfolio voice pulse
 * that replaces scanning Discord + Paperclip + many agent streams.
 *
 * Keep Python mirror in tests/test_pwa_onboarding.py in sync.
 */

/** localStorage key when user dismisses the install strip. */
export const INSTALL_STRIP_DISMISS_KEY = "advoi_install_strip_dismissed";

/** Frame id the morning pulse CTA runs (Option D / systems-pulse). */
export const MORNING_PULSE_FRAME_ID = "systems_pulse";

/** Custom event name VoiceSession listens for (detail.frameId, detail.refresh). */
export const RUN_FRAME_EVENT = "advoi:run-frame";

export type DisplayModeInput = {
  /** matchMedia("(display-mode: standalone)").matches */
  standaloneMedia: boolean;
  /** iOS Safari: (navigator as Navigator & { standalone?: boolean }).standalone */
  iosStandalone: boolean;
  /** Optional: matchMedia("(display-mode: minimal-ui)").matches */
  minimalUiMedia?: boolean;
};

/**
 * True when the app is running as an installed PWA (standalone / iOS home screen).
 */
export function isStandaloneDisplay(input: DisplayModeInput): boolean {
  if (input.standaloneMedia) return true;
  if (input.iosStandalone) return true;
  if (input.minimalUiMedia) return true;
  return false;
}

/**
 * Read display mode from a Window-like object. Safe for SSR when window is undefined.
 */
export function readDisplayMode(
  win: {
    matchMedia?: (q: string) => { matches: boolean };
    navigator?: { standalone?: boolean } | Navigator;
  } | null | undefined,
): DisplayModeInput {
  if (win == null || typeof win.matchMedia !== "function") {
    return { standaloneMedia: false, iosStandalone: false, minimalUiMedia: false };
  }
  const standaloneMedia = Boolean(win.matchMedia("(display-mode: standalone)").matches);
  const minimalUiMedia = Boolean(win.matchMedia("(display-mode: minimal-ui)").matches);
  const nav = win.navigator as { standalone?: boolean } | undefined;
  const iosStandalone = Boolean(nav?.standalone);
  return { standaloneMedia, iosStandalone, minimalUiMedia };
}

export type InstallStripModel = {
  /** Whether the strip should render. */
  visible: boolean;
  /** True when already installed (standalone). */
  isStandalone: boolean;
  title: string;
  body: string;
  /** Primary action label (browser install prompt when available). */
  installLabel: string;
  /** Secondary dismiss label. */
  dismissLabel: string;
  /** Platform hint for manual A2HS (shown when no deferred prompt). */
  howToHint: string;
};

export type InstallPlatform = "ios" | "android" | "desktop" | "unknown";

export type InstallStripInput = {
  isStandalone: boolean;
  /** User previously dismissed the strip. */
  dismissed: boolean;
  /** True when beforeinstallprompt was captured (Chrome/Edge). */
  hasDeferredPrompt?: boolean;
  /** Coarse platform hint for how-to copy. */
  platform?: InstallPlatform;
};

/**
 * Build the Add-to-Home-Screen install strip presentation.
 * Hidden when already standalone or dismissed.
 */
export function installStripModel(input: InstallStripInput): InstallStripModel {
  const isStandalone = Boolean(input.isStandalone);
  const dismissed = Boolean(input.dismissed);
  const visible = !isStandalone && !dismissed;

  const platform = input.platform ?? "unknown";
  let howToHint: string;
  if (platform === "ios") {
    howToHint = "Safari: Share → Add to Home Screen";
  } else if (platform === "android") {
    howToHint = input.hasDeferredPrompt
      ? "Tap Install for a home-screen icon"
      : "Browser menu → Install app / Add to Home screen";
  } else if (platform === "desktop") {
    howToHint = input.hasDeferredPrompt
      ? "Tap Install for a desktop app shortcut"
      : "Use the browser install icon in the address bar";
  } else {
    howToHint = input.hasDeferredPrompt
      ? "Tap Install to pin ADVoi"
      : "Use your browser menu: Add to Home Screen / Install app";
  }

  return {
    visible,
    isStandalone,
    title: "Add to Home Screen",
    body: "One tap for your morning portfolio pulse — no browser chrome.",
    installLabel: input.hasDeferredPrompt ? "Install" : "How to install",
    dismissLabel: "Not now",
    howToHint,
  };
}

export type MorningPulseCtaModel = {
  eyebrow: string;
  title: string;
  body: string;
  buttonLabel: string;
  frameId: string;
  /** Secondary meta line (duration positioning). */
  durationHint: string;
};

/**
 * 60s morning pulse CTA copy — portfolio voice pulse positioning (moat Pattern F).
 */
export function morningPulseCtaModel(): MorningPulseCtaModel {
  return {
    eyebrow: "Daily loop · Pattern F",
    title: "60s morning pulse",
    body:
      "One spoken portfolio pulse: fleet, briefs, and agent warmth — instead of scanning Discord, Paperclip, and agent streams.",
    buttonLabel: "Start morning pulse",
    frameId: MORNING_PULSE_FRAME_ID,
    durationHint: "About 60 seconds · systems pulse",
  };
}

/**
 * Coarse UA platform for install how-to copy (pure, injectable for tests).
 */
export function detectPlatform(userAgent: string | null | undefined): InstallPlatform {
  const ua = (userAgent || "").toLowerCase();
  if (!ua) return "unknown";
  if (/iphone|ipad|ipod/.test(ua)) return "ios";
  if (/android/.test(ua)) return "android";
  if (/windows|macintosh|linux/.test(ua) && !/mobile/.test(ua)) return "desktop";
  return "unknown";
}

/**
 * Parse dismissed flag from storage string.
 */
export function isInstallStripDismissed(stored: string | null | undefined): boolean {
  if (stored == null) return false;
  const v = String(stored).trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
