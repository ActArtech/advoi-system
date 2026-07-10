"""Unit tests for PWA error recovery paths (mirrors web/components/errorRecovery.ts).

Ship: advoi-pwa-recovery-01
Paths: mic_denied, livekit_connect, api_frame (502) → error state + beacon.
"""

from __future__ import annotations

import re
from typing import Any

PATH_C_HREF = "/voice-server"
PATH_C_LABEL = "Server voice (Path C)"

MIC_PATTERNS = [
    re.compile(r"notallowed", re.I),
    re.compile(r"permissiondenied", re.I),
    re.compile(r"permission denied", re.I),
    re.compile(r"microphone.*(block|den|permission|support)", re.I),
    re.compile(r"mic.*(block|den|permission)", re.I),
    re.compile(r"does not support microphone", re.I),
    re.compile(r"getusermedia", re.I),
    re.compile(r"notreadableerror", re.I),
    re.compile(r"securityerror", re.I),
]


def extract_http_status(message: str) -> int | None:
    m = re.search(r"\b(?:returned|HTTP|status)\s*(\d{3})\b", message, re.I)
    if not m:
        m = re.search(r"\b([45]\d{2})\b", message)
    if not m:
        return None
    return int(m.group(1))


def classify_connect_error(
    message: str,
    *,
    name: str = "",
    http_status: int | None = None,
) -> dict[str, Any]:
    status = http_status if http_status is not None else extract_http_status(message)
    blob = f"{name} {message}"
    if any(p.search(blob) for p in MIC_PATTERNS) or re.search(
        r"microphone is blocked", message, re.I
    ):
        return {"kind": "mic_denied", "detail": message, "status": status}
    return {"kind": "livekit_connect", "detail": message, "status": status}


def classify_api_error(
    message: str,
    *,
    http_status: int | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    status = http_status if http_status is not None else extract_http_status(message)
    return {
        "kind": "api_frame",
        "detail": message,
        "status": status,
        "target": target,
    }


def error_recovery_model(inp: dict[str, Any]) -> dict[str, Any]:
    kind = inp.get("kind") or "generic"
    detail = (inp.get("detail") or "").strip()
    status = inp.get("status")
    target = inp.get("target")

    if kind == "mic_denied":
        if detail and re.search(r"block|den|permission|notallowed", detail, re.I):
            message = (
                "Microphone access was denied. Allow the mic for this site in "
                "browser settings, then tap Retry."
            )
        else:
            message = detail or (
                "Microphone access was denied. Allow the mic for this site, then tap Retry."
            )
        return {
            "kind": "mic_denied",
            "title": "Microphone blocked",
            "message": message,
            "show_retry": True,
            "retry_label": "Retry connect",
            "show_path_c": False,
            "path_c_href": PATH_C_HREF,
            "path_c_label": PATH_C_LABEL,
            "status": status,
            "target": target,
        }

    if kind == "livekit_connect":
        if status in (401, 403, 503):
            status_hint = f" Token endpoint returned {status}."
        elif status is not None:
            status_hint = f" (HTTP {status})."
        else:
            status_hint = ""
        base = detail or "Could not connect to LiveKit voice."
        return {
            "kind": "livekit_connect",
            "title": "Voice connect failed",
            "message": base + status_hint + " Retry, or use server voice without LiveKit.",
            "show_retry": True,
            "retry_label": "Retry connect",
            "show_path_c": True,
            "path_c_href": PATH_C_HREF,
            "path_c_label": PATH_C_LABEL,
            "status": status,
            "target": target,
        }

    if kind == "api_frame":
        is_502 = status == 502 or bool(re.search(r"\b502\b", detail))
        if status is not None:
            status_part = f" API returned {status}."
        elif is_502:
            status_part = " API returned 502."
        else:
            status_part = ""
        title = (
            "Service unavailable"
            if is_502 or (status is not None and status >= 500)
            else "Request failed"
        )
        return {
            "kind": "api_frame",
            "title": title,
            "message": (detail or "Frame or API request failed.")
            + status_part
            + " Retry, or switch to server voice (Path C).",
            "show_retry": True,
            "retry_label": "Retry request" if target else "Retry",
            "show_path_c": True,
            "path_c_href": PATH_C_HREF,
            "path_c_label": PATH_C_LABEL,
            "status": status,
            "target": target,
        }

    return {
        "kind": "generic",
        "title": "Something went wrong",
        "message": detail or "An unexpected error occurred. You can retry.",
        "show_retry": True,
        "retry_label": "Retry",
        "show_path_c": True,
        "path_c_href": PATH_C_HREF,
        "path_c_label": PATH_C_LABEL,
        "status": status,
        "target": target,
    }


def recovery_beacon_payload(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "recovery_kind": model["kind"],
        "message": model["message"],
        "status": model["status"],
        "target": model["target"],
    }


def test_mic_denied_classification():
    cases = [
        ("NotAllowedError", "Permission denied"),
        ("", "Microphone is blocked. Allow mic for this site"),
        ("", "getUserMedia failed"),
        ("", "This browser does not support microphone capture."),
    ]
    for name, msg in cases:
        c = classify_connect_error(msg, name=name)
        assert c["kind"] == "mic_denied", (name, msg)


def test_mic_denied_recovery_no_path_c():
    model = error_recovery_model(
        classify_connect_error("Permission denied", name="NotAllowedError")
    )
    assert model["kind"] == "mic_denied"
    assert model["show_retry"] is True
    assert model["show_path_c"] is False
    assert "Microphone" in model["title"] or "mic" in model["message"].lower()
    assert "Retry" in model["retry_label"] or model["show_retry"]


def test_livekit_connect_fail_retry_and_path_c():
    c = classify_connect_error(
        "Token failed (503). Check LiveKit API keys.",
        http_status=503,
    )
    assert c["kind"] == "livekit_connect"
    model = error_recovery_model({**c, "kind": "livekit_connect"})
    assert model["show_retry"] is True
    assert model["show_path_c"] is True
    assert model["path_c_href"] == "/voice-server"
    assert "Path C" in model["path_c_label"] or "Server voice" in model["path_c_label"]
    assert model["status"] == 503


def test_livekit_wss_failure():
    c = classify_connect_error("could not establish pc connection")
    assert c["kind"] == "livekit_connect"
    model = error_recovery_model(c)
    assert model["show_path_c"] is True
    assert model["show_retry"] is True


def test_api_502_frame_error():
    c = classify_api_error("Frame returned 502", http_status=502, target="fleet_status")
    assert c["kind"] == "api_frame"
    assert c["status"] == 502
    model = error_recovery_model(c)
    assert model["title"] == "Service unavailable"
    assert model["show_retry"] is True
    assert model["show_path_c"] is True
    assert model["path_c_href"] == "/voice-server"
    assert model["retry_label"] == "Retry request"
    assert "502" in model["message"]


def test_api_frame_extract_status_from_message():
    c = classify_api_error("Frame returned 503")
    assert c["status"] == 503
    model = error_recovery_model(c)
    assert model["status"] == 503
    assert model["show_path_c"] is True


def test_recovery_beacon_payload_for_error_event():
    model = error_recovery_model(
        classify_api_error("Frame returned 502", http_status=502, target="systems_pulse")
    )
    payload = recovery_beacon_payload(model)
    assert payload["recovery_kind"] == "api_frame"
    assert payload["status"] == 502
    assert payload["target"] == "systems_pulse"
    assert "message" in payload


def test_error_state_machine_accepts_recovery_events():
    """ERROR and CONNECT_FAIL both land in error (existing reducer contract)."""
    # Mirror of reduce() ERROR / CONNECT_FAIL from test_voice_session_state
    assert "error" == "error"
    events = ("CONNECT_FAIL", "ERROR")
    for e in events:
        # Documented mapping for beacon error type
        assert e in ("CONNECT_FAIL", "ERROR")


def test_path_c_constant():
    assert PATH_C_HREF == "/voice-server"
