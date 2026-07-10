"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  INSTALL_STRIP_DISMISS_KEY,
  RUN_FRAME_EVENT,
  detectPlatform,
  installStripModel,
  isInstallStripDismissed,
  isStandaloneDisplay,
  morningPulseCtaModel,
  readDisplayMode,
  type InstallPlatform,
} from "./pwaOnboarding";
import styles from "./PwaHomeOnboarding.module.css";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

/**
 * Home-only onboarding surface (no new routes):
 * 1. Add to Home Screen install strip (browser vs standalone)
 * 2. 60s morning pulse CTA → systems_pulse via advoi:run-frame
 */
export function PwaHomeOnboarding() {
  const [standalone, setStandalone] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(
    null,
  );
  const [showHowTo, setShowHowTo] = useState(false);
  const [platform, setPlatform] = useState<InstallPlatform>("unknown");
  const [hydrated, setHydrated] = useState(false);

  const pulse = useMemo(() => morningPulseCtaModel(), []);

  useEffect(() => {
    const mode = readDisplayMode(window);
    setStandalone(isStandaloneDisplay(mode));
    setPlatform(detectPlatform(navigator.userAgent));
    try {
      setDismissed(isInstallStripDismissed(localStorage.getItem(INSTALL_STRIP_DISMISS_KEY)));
    } catch {
      setDismissed(false);
    }
    setHydrated(true);

    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBip);

    const mq = window.matchMedia("(display-mode: standalone)");
    const onMode = () => {
      setStandalone(isStandaloneDisplay(readDisplayMode(window)));
    };
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", onMode);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", onBip);
      if (typeof mq.removeEventListener === "function") {
        mq.removeEventListener("change", onMode);
      }
    };
  }, []);

  const strip = useMemo(
    () =>
      installStripModel({
        isStandalone: standalone,
        dismissed,
        hasDeferredPrompt: Boolean(deferredPrompt),
        platform,
      }),
    [standalone, dismissed, deferredPrompt, platform],
  );

  const dismissStrip = useCallback(() => {
    setDismissed(true);
    setShowHowTo(false);
    try {
      localStorage.setItem(INSTALL_STRIP_DISMISS_KEY, "1");
    } catch {
      /* ignore quota / private mode */
    }
  }, []);

  const onInstallClick = useCallback(async () => {
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt();
        await deferredPrompt.userChoice;
      } catch {
        /* user dismissed or browser blocked */
      }
      setDeferredPrompt(null);
      return;
    }
    setShowHowTo((v) => !v);
  }, [deferredPrompt]);

  const startMorningPulse = useCallback(() => {
    window.dispatchEvent(
      new CustomEvent(RUN_FRAME_EVENT, {
        detail: { frameId: pulse.frameId, refresh: true, source: "morning_pulse_cta" },
      }),
    );
    const session = document.querySelector("[data-testid='ui-state-chip']");
    session?.scrollIntoView?.({ behavior: "smooth", block: "center" });
  }, [pulse.frameId]);

  return (
    <div className={styles.wrap} data-testid="pwa-home-onboarding">
      {hydrated && strip.visible ? (
        <aside
          className={styles.installStrip}
          data-testid="install-strip"
          data-standalone="false"
          data-platform={platform}
          data-has-prompt={deferredPrompt ? "true" : "false"}
          role="region"
          aria-label="Add to Home Screen"
        >
          <div className={styles.installText}>
            <p className={styles.installTitle}>{strip.title}</p>
            <p className={styles.installBody}>{strip.body}</p>
            {showHowTo ? (
              <p className={styles.installHowTo} data-testid="install-howto">
                {strip.howToHint}
              </p>
            ) : null}
          </div>
          <div className={styles.installActions}>
            <button
              type="button"
              className={styles.installBtn}
              data-testid="install-strip-action"
              onClick={() => void onInstallClick()}
            >
              {strip.installLabel}
            </button>
            <button
              type="button"
              className={styles.dismissBtn}
              data-testid="install-strip-dismiss"
              onClick={dismissStrip}
            >
              {strip.dismissLabel}
            </button>
          </div>
        </aside>
      ) : null}

      {hydrated && standalone ? (
        <p
          className={styles.standaloneBadge}
          data-testid="install-strip-standalone"
          data-standalone="true"
        >
          Installed · home screen mode
        </p>
      ) : null}

      <section
        className={styles.pulseCta}
        data-testid="morning-pulse-cta"
        data-frame-id={pulse.frameId}
        aria-label="60 second morning pulse"
      >
        <p className={styles.pulseEyebrow}>{pulse.eyebrow}</p>
        <h2 className={styles.pulseTitle}>{pulse.title}</h2>
        <p className={styles.pulseBody}>{pulse.body}</p>
        <div className={styles.pulseRow}>
          <button
            type="button"
            className={styles.pulseBtn}
            data-testid="morning-pulse-start"
            onClick={startMorningPulse}
          >
            {pulse.buttonLabel}
          </button>
          <span className={styles.pulseMeta}>{pulse.durationHint}</span>
        </div>
      </section>
    </div>
  );
}
