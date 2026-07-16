"""Bridge ADVoi voice/API to FirstMate fm-hermes-trigger.sh (crew spawn path)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Literal

from advoi.copy_style import plain_copy
from advoi.fleet.bridge import resolve_fleet_exec
from advoi.portfolio.ecr import resolve_execution_target
from advoi.routing.frame_runner import (
    _fleet_backlog_snapshot,
    _fleet_profile_snapshot,
    _fleet_root,
    _session_scope_fleet_slug,
)

_LOGGER = logging.getLogger(__name__)

FleetVoiceAction = Literal[
    "wake_firstmate",
    "start_development",
    "run_next_backlog",
    "fleet_stop",
]

# Operator action → fm-hermes-trigger verb (single argv after scripts/fm-bridge.sh).
# Multi-step actions (start_development, run_next_backlog) compose arm/stop + work.
FLEET_ACTION_BRIDGE_VERB: dict[FleetVoiceAction, str] = {
    "wake_firstmate": "arm",
    "fleet_stop": "stop",
}

_PROJECT_RE = re.compile(
    r"\b(?:on|for|project)\s+([a-z][a-z0-9_-]+)\b",
    re.IGNORECASE,
)


def _fleet_mock() -> bool:
    return os.getenv("ADVOI_FLEET_MOCK", "false").lower() in {"1", "true", "yes"}


def resolve_active_project(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip().lower()
    target = resolve_execution_target()
    if target.get("fleet_slug"):
        return str(target["fleet_slug"]).strip().lower()
    profile = _fleet_profile_snapshot(_fleet_root() / "data")
    return (profile.get("active_slug") or os.getenv("FM_HERMES_PROJECT") or "clapart").strip()


def peek_fleet_backlog(project: str | None = None) -> dict[str, Any]:
    data_dir = _fleet_root() / "data"
    # Explicit project or session/ECR resolution (same rules as Fleet Scout).
    slug = project or resolve_active_project()
    scope = bool(project) or bool(_session_scope_fleet_slug())
    backlog = _fleet_backlog_snapshot(data_dir, slug, scope_filter=scope)
    queued = backlog.get("queued") or []
    in_flight = backlog.get("in_flight") or []
    return {
        "project": slug,
        "queued": queued,
        "in_flight": in_flight,
        "next": queued[0] if queued else None,
        "backlog_found": backlog.get("backlog_found", False),
    }


def next_backlog_item(project: str | None = None) -> str | None:
    return peek_fleet_backlog(project).get("next")


def extract_project_slug(transcript: str) -> str | None:
    match = _PROJECT_RE.search(transcript or "")
    return match.group(1).lower() if match else None


def classify_fleet_voice_intent(transcript: str) -> FleetVoiceAction | None:
    text = (transcript or "").strip().lower()
    if not text:
        return None

    if any(
        p in text
        for p in (
            "stop fleet",
            "stop firstmate",
            "disarm fleet",
            "pause firstmate",
            "halt fleet",
        )
    ):
        return "fleet_stop"

    if any(
        p in text
        for p in (
            "run next backlog",
            "next backlog item",
            "work next item",
            "dispatch next",
            "run the next backlog",
            "run the next backlog item",
            "run next backlog item",
            "next queued item",
            "pick up next task",
        )
    ):
        return "run_next_backlog"

    if any(
        p in text
        for p in (
            "start development",
            "begin development",
            "start dev",
            "begin dev",
            "kick off development",
            "start coding",
            "start building",
        )
    ):
        return "start_development"

    if any(
        p in text
        for p in (
            "wake firstmate",
            "wake first mate",
            "arm fleet",
            "arm firstmate",
            "arm first mate",
            "start fleet loop",
            "start the fleet",
            "wake the captain",
            "wake captain",
        )
    ):
        return "wake_firstmate"

    return None


def fleet_action_needs_confirm(transcript: str) -> bool:
    """Deprecated: use guardian.evaluate_fleet_confirmation for a specific action."""
    from advoi.guardian.confirmation import transcript_has_explicit_confirm

    return not transcript_has_explicit_confirm(transcript)


def fleet_confirm_prompt(action: FleetVoiceAction) -> str:
    from advoi.guardian.confirmation import fleet_confirmation_prompt

    return fleet_confirmation_prompt(action)


def _output_excerpt(output: str | None, *, limit: int = 240) -> str:
    text = (output or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


async def _emit_fleet_trigger_event(
    result: dict[str, Any],
    *,
    action: str | None = None,
    caller: str = "api",
    guardian_status: str | None = None,
) -> None:
    """Append PEL row after a fleet bridge invoke (moat R1 / T0)."""
    from advoi.analytics.pel import EventSource, EventType, safe_append_event

    project = str(result.get("project") or "unknown")
    status = str(result.get("status") or "unknown")
    mock = status == "mock" or _fleet_mock()
    await safe_append_event(
        venture_id=project,
        source=EventSource.FLEET,
        event_type=EventType.FLEET_TRIGGER,
        payload={
            "action": action or result.get("action"),
            "project": project,
            "mock": mock,
            "status": status,
            "exit_code": result.get("exit_code"),
            "output_excerpt": _output_excerpt(result.get("output")),
            "message": result.get("message"),
            "caller": caller,
            "ok": bool(result.get("ok")),
        },
        guardian_status=guardian_status or ("allowed" if result.get("ok") else None),
        execution_ref=result.get("bridge") if isinstance(result.get("bridge"), str) else None,
    )


async def _emit_fleet_gate_event(
    *,
    action: str,
    project: str,
    proceed: bool,
    caller: str = "voice",
) -> None:
    from advoi.analytics.pel import EventSource, EventType, GuardianStatus, safe_append_event

    await safe_append_event(
        venture_id=project or "unknown",
        source=EventSource.FLEET,
        event_type=EventType.GUARDIAN_GATE,
        payload={
            "action": action,
            "project": project,
            "proceed": proceed,
            "caller": caller,
        },
        guardian_status=(GuardianStatus.ALLOWED if proceed else GuardianStatus.PENDING),
    )


def _guardian_permits_fleet_invoke(
    *,
    guardian_allowed: bool,
    guardian_status: str | None,
) -> bool:
    """True when confirmation policy is off, or caller proved Guardian approval.

    Production callers must either:
    - use :func:`fleet_trigger_from_voice` (gates then sets guardian_status), or
    - pass ``guardian_allowed=True`` / ``guardian_status="allowed"`` only after
      :func:`advoi.guardian.confirmation.evaluate_fleet_confirmation` returned proceed.
    """
    from advoi.guardian.confirmation import global_confirmation_enabled

    if not global_confirmation_enabled():
        return True
    if guardian_allowed:
        return True
    if (guardian_status or "").strip().lower() == "allowed":
        return True
    return False


async def invoke_fleet_trigger(
    message: str,
    *,
    project: str | None = None,
    caller: str = "api",
    action: str | None = None,
    guardian_status: str | None = None,
    guardian_allowed: bool = False,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Invoke fm-bridge once. Optional ``idempotency_key`` dedupes for 60s.

    When ``ADVOI_CONFIRMATION_REQUIRED`` is on, callers must pass
    ``guardian_allowed=True`` or ``guardian_status="allowed"`` after a Guardian
    gate. Prefer :func:`fleet_trigger_from_voice` for structured high-risk actions.

    See ``advoi.fleet.idempotency`` for the header/param contract.
    """
    from advoi.fleet.idempotency import (
        get_idempotent_result,
        normalize_idempotency_key,
        store_idempotent_result,
    )

    key = normalize_idempotency_key(idempotency_key)
    cached = get_idempotent_result(key)
    if cached is not None:
        return cached

    slug = resolve_active_project(project)
    msg = message.strip()
    exec_argv = resolve_fleet_exec()

    def _finish(result: dict[str, Any]) -> dict[str, Any]:
        store_idempotent_result(key, result)
        if key:
            return {**result, "idempotency_key": key}
        return result

    if not _guardian_permits_fleet_invoke(
        guardian_allowed=guardian_allowed,
        guardian_status=guardian_status,
    ):
        result = {
            "ok": False,
            "status": "guardian_required",
            "message": msg,
            "project": slug,
            "bridge": exec_argv[1] if len(exec_argv) > 1 else None,
            "guardian": True,
            "output": "Guardian approval required before fm-bridge invoke.",
        }
        await _emit_fleet_trigger_event(
            result,
            action=action,
            caller=caller,
            guardian_status="pending",
        )
        return _finish(result)

    # Post-gate: normalize PEL status so default emit is not silently "allowed".
    effective_guardian = guardian_status or ("allowed" if guardian_allowed else None)

    if _fleet_mock():
        result = {
            "ok": True,
            "status": "mock",
            "message": msg,
            "project": slug,
            "bridge": exec_argv[1],
            "output": f"OK: mock fleet trigger — {msg} @ {slug}",
        }
        await _emit_fleet_trigger_event(
            result,
            action=action,
            caller=caller,
            guardian_status=effective_guardian or "allowed",
        )
        return _finish(result)

    script_path = Path(exec_argv[1])
    if not script_path.is_file():
        result = {
            "ok": False,
            "status": "bridge_script_missing",
            "path": str(script_path),
            "message": msg,
            "project": slug,
        }
        await _emit_fleet_trigger_event(
            result,
            action=action,
            caller=caller,
            guardian_status=effective_guardian or "error",
        )
        return _finish(result)

    env = os.environ.copy()
    env["FM_HERMES_PROJECT"] = slug
    env.setdefault("FIRSTMATE_CONTAINER", "firstmate-fleet")

    proc = await asyncio.create_subprocess_exec(
        *exec_argv,
        msg,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    ok = proc.returncode == 0
    result = {
        "ok": ok,
        "status": "dispatched" if ok else "failed",
        "exit_code": proc.returncode,
        "output": output,
        "message": msg,
        "project": slug,
        "bridge": exec_argv[1],
    }
    await _emit_fleet_trigger_event(
        result,
        action=action,
        caller=caller,
        guardian_status=effective_guardian or ("allowed" if ok else "error"),
    )
    return _finish(result)


async def fleet_trigger_from_voice(
    action: FleetVoiceAction,
    transcript: str,
    *,
    confirmed: bool = False,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Voice/API fleet action path with optional request-level idempotency key.

    When ``idempotency_key`` is set, the **whole action result** is cached for
    60s so multi-step actions (e.g. start_development = arm + work) do not
    double-dispatch on client retries. Inner ``invoke_fleet_trigger`` calls
    intentionally omit the key.
    """
    from advoi.fleet.idempotency import (
        get_idempotent_result,
        normalize_idempotency_key,
        store_idempotent_result,
    )
    from advoi.guardian.confirmation import evaluate_fleet_confirmation

    key = normalize_idempotency_key(idempotency_key)
    cached = get_idempotent_result(key)
    if cached is not None:
        return cached

    def _finish(result: dict[str, Any]) -> dict[str, Any]:
        store_idempotent_result(key, result)
        if key:
            return {**result, "idempotency_key": key}
        return result

    project = extract_project_slug(transcript) or resolve_active_project()
    gate = evaluate_fleet_confirmation(
        action,
        confirmed=confirmed,
        transcript=transcript,
    )
    if not gate["proceed"]:
        await _emit_fleet_gate_event(
            action=action,
            project=project,
            proceed=False,
            caller="voice",
        )
        # Do not store confirmation_required — client must retry with confirmed.
        return {
            "ok": False,
            "status": "confirmation_required",
            "action": action,
            "project": project,
            "prompt": gate.get("prompt", fleet_confirm_prompt(action)),
            "guardian": True,
        }

    await _emit_fleet_gate_event(
        action=action,
        project=project,
        proceed=True,
        caller="voice",
    )

    if action == "fleet_stop":
        result = await invoke_fleet_trigger(
            FLEET_ACTION_BRIDGE_VERB["fleet_stop"],
            project=project,
            caller="voice",
            action=action,
            guardian_status="allowed",
        )
        spoken = (
            f"FirstMate fleet loop stopped on {project}."
            if result.get("ok")
            else f"Could not stop FirstMate fleet: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        return _finish(result)

    if action == "wake_firstmate":
        result = await invoke_fleet_trigger(
            FLEET_ACTION_BRIDGE_VERB["wake_firstmate"],
            project=project,
            caller="voice",
            action=action,
            guardian_status="allowed",
        )
        spoken = (
            f"FirstMate fleet loop armed on {project}. Captain will pick up from the wake queue."
            if result.get("ok")
            else f"Could not wake FirstMate: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        return _finish(result)

    if action == "run_next_backlog":
        item = next_backlog_item(project)
        if not item:
            empty = {
                "ok": False,
                "status": "empty_backlog",
                "action": action,
                "project": project,
                "spoken": plain_copy(
                    f"No queued backlog items for {project}. Say fleet status to hear the queue."
                ),
            }
            return _finish(empty)
        result = await invoke_fleet_trigger(
            f"work {item}",
            project=project,
            caller="voice",
            action=action,
            guardian_status="allowed",
        )
        spoken = (
            f"Dispatched next backlog item {item} on {project} to the FirstMate captain."
            if result.get("ok")
            else f"Could not dispatch backlog item: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        result["task"] = item
        return _finish(result)

    if action == "start_development":
        arm = await invoke_fleet_trigger(
            FLEET_ACTION_BRIDGE_VERB["wake_firstmate"],
            project=project,
            caller="voice",
            action=action,
            guardian_status="allowed",
        )
        if not arm.get("ok"):
            arm["spoken"] = plain_copy(
                f"Could not arm FirstMate on {project}: {arm.get('output', arm.get('status'))}"
            )
            arm["action"] = action
            return _finish(arm)

        item = next_backlog_item(project)
        if item:
            work = await invoke_fleet_trigger(
                f"work {item}",
                project=project,
                caller="voice",
                action=action,
                guardian_status="allowed",
            )
            if work.get("ok"):
                spoken = (
                    f"Development started on {project}. Fleet loop armed and captain dispatched "
                    f"next backlog item {item}."
                )
                work["spoken"] = plain_copy(spoken)
                work["action"] = action
                work["armed"] = True
                work["task"] = item
                return _finish(work)
            spoken = (
                f"Fleet armed on {project} but work dispatch failed: "
                f"{work.get('output', work.get('status'))}"
            )
            arm["spoken"] = plain_copy(spoken)
            arm["action"] = action
            arm["armed"] = True
            return _finish(arm)

        work = await invoke_fleet_trigger(
            f"work continue development on {project}",
            project=project,
            caller="voice",
            action=action,
            guardian_status="allowed",
        )
        spoken = (
            f"Development started on {project}. Fleet loop armed and captain notified."
            if work.get("ok")
            else (
                f"Fleet armed on {project} but captain dispatch failed: "
                f"{work.get('output', work.get('status'))}"
            )
        )
        work["spoken"] = plain_copy(spoken)
        work["action"] = action
        work["armed"] = True
        return _finish(work)

    return {"ok": False, "status": "unknown_action", "action": action}
