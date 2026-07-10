"""Unit tests for PWA home onboarding (mirrors web/components/pwaOnboarding.ts).

Python port keeps CI green without a JS test runner. Keep copy/rules in sync.
"""

from __future__ import annotations

from typing import Any

INSTALL_STRIP_DISMISS_KEY = "advoi_install_strip_dismissed"
MORNING_PULSE_FRAME_ID = "systems_pulse"
RUN_FRAME_EVENT = "advoi:run-frame"


def is_standalone_display(
    *,
    standalone_media: bool,
    ios_standalone: bool,
    minimal_ui_media: bool = False,
) -> bool:
    if standalone_media:
        return True
    if ios_standalone:
        return True
    if minimal_ui_media:
        return True
    return False


def install_strip_model(
    *,
    is_standalone: bool,
    dismissed: bool,
    has_deferred_prompt: bool = False,
    platform: str = "unknown",
) -> dict[str, Any]:
    """Mirror of installStripModel in web/components/pwaOnboarding.ts."""
    visible = (not is_standalone) and (not dismissed)

    if platform == "ios":
        how_to = "Safari: Share → Add to Home Screen"
    elif platform == "android":
        how_to = (
            "Tap Install for a home-screen icon"
            if has_deferred_prompt
            else "Browser menu → Install app / Add to Home screen"
        )
    elif platform == "desktop":
        how_to = (
            "Tap Install for a desktop app shortcut"
            if has_deferred_prompt
            else "Use the browser install icon in the address bar"
        )
    else:
        how_to = (
            "Tap Install to pin ADVoi"
            if has_deferred_prompt
            else "Use your browser menu: Add to Home Screen / Install app"
        )

    return {
        "visible": visible,
        "is_standalone": bool(is_standalone),
        "title": "Add to Home Screen",
        "body": "One tap for your morning portfolio pulse — no browser chrome.",
        "install_label": "Install" if has_deferred_prompt else "How to install",
        "dismiss_label": "Not now",
        "how_to_hint": how_to,
    }


def morning_pulse_cta_model() -> dict[str, Any]:
    """Mirror of morningPulseCtaModel — portfolio voice pulse positioning."""
    return {
        "eyebrow": "Daily loop · Pattern F",
        "title": "60s morning pulse",
        "body": (
            "One spoken portfolio pulse: fleet, briefs, and agent warmth — "
            "instead of scanning Discord, Paperclip, and agent streams."
        ),
        "button_label": "Start morning pulse",
        "frame_id": MORNING_PULSE_FRAME_ID,
        "duration_hint": "About 60 seconds · systems pulse",
    }


def detect_platform(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    if not ua:
        return "unknown"
    if any(x in ua for x in ("iphone", "ipad", "ipod")):
        return "ios"
    if "android" in ua:
        return "android"
    if any(x in ua for x in ("windows", "macintosh", "linux")) and "mobile" not in ua:
        return "desktop"
    return "unknown"


def is_install_strip_dismissed(stored: str | None) -> bool:
    if stored is None:
        return False
    v = str(stored).strip().lower()
    return v in {"1", "true", "yes"}


# --- tests ---


def test_standalone_true_when_display_mode_standalone():
    assert is_standalone_display(standalone_media=True, ios_standalone=False) is True


def test_standalone_true_on_ios_home_screen():
    assert is_standalone_display(standalone_media=False, ios_standalone=True) is True


def test_standalone_false_in_browser_tab():
    assert is_standalone_display(standalone_media=False, ios_standalone=False) is False


def test_install_strip_hidden_when_standalone():
    m = install_strip_model(is_standalone=True, dismissed=False)
    assert m["visible"] is False
    assert m["is_standalone"] is True


def test_install_strip_hidden_when_dismissed():
    m = install_strip_model(is_standalone=False, dismissed=True)
    assert m["visible"] is False


def test_install_strip_visible_in_browser():
    m = install_strip_model(
        is_standalone=False,
        dismissed=False,
        has_deferred_prompt=False,
        platform="ios",
    )
    assert m["visible"] is True
    assert m["title"] == "Add to Home Screen"
    assert "morning portfolio pulse" in m["body"]
    assert m["install_label"] == "How to install"
    assert "Share" in m["how_to_hint"]
    assert m["dismiss_label"] == "Not now"


def test_install_strip_prompt_label_when_bip_available():
    m = install_strip_model(
        is_standalone=False,
        dismissed=False,
        has_deferred_prompt=True,
        platform="android",
    )
    assert m["install_label"] == "Install"
    assert "Tap Install" in m["how_to_hint"]


def test_morning_pulse_cta_aligned_with_portfolio_voice():
    m = morning_pulse_cta_model()
    assert m["frame_id"] == "systems_pulse"
    assert m["frame_id"] == MORNING_PULSE_FRAME_ID
    assert "60" in m["title"]
    assert "portfolio pulse" in m["body"]
    assert "Discord" in m["body"]
    assert "Paperclip" in m["body"]
    assert m["button_label"] == "Start morning pulse"
    assert "60" in m["duration_hint"]
    assert "systems pulse" in m["duration_hint"]
    assert "Pattern F" in m["eyebrow"]


def test_detect_platform_ios_android_desktop():
    assert detect_platform("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)") == "ios"
    assert detect_platform("Mozilla/5.0 (Linux; Android 14)") == "android"
    assert detect_platform("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120") == "desktop"
    assert detect_platform(None) == "unknown"
    assert detect_platform("") == "unknown"


def test_dismissed_storage_parse():
    assert is_install_strip_dismissed("1") is True
    assert is_install_strip_dismissed("true") is True
    assert is_install_strip_dismissed(None) is False
    assert is_install_strip_dismissed("0") is False


def test_constants_stable_for_wiring():
    assert INSTALL_STRIP_DISMISS_KEY == "advoi_install_strip_dismissed"
    assert RUN_FRAME_EVENT == "advoi:run-frame"
    assert MORNING_PULSE_FRAME_ID == "systems_pulse"
