"""Bridge ADVoi voice/API to FirstMate fm-hermes-trigger.sh (crew spawn path)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Literal

from advoi.copy_style import plain_copy
from advoi.routing.frame_runner import (
    _fleet_backlog_snapshot,
    _fleet_profile_snapshot,
    _fleet_root,
)

_LOGGER = logging.getLogger(__name__)

FleetVoiceAction = Literal[
    "wake_firstmate",
    "start_development",
    "run_next_backlog",
    "fleet_stop",
]

_PROJECT_RE = re.compile(
    r"\b(?:on|for|project)\s+([a-z][a-z0-9_-]+)\b",
    re.IGNORECASE,
)


def _trigger_script() -> Path:
    return Path(
        os.getenv(
            "FIRSTMATE_TRIGGER_SCRIPT",
            "/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh",
        )
    )


def _fleet_mock() -> bool:
    return os.getenv("ADVOI_FLEET_MOCK", "false").lower() in {"1", "true", "yes"}


def resolve_active_project(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip().lower()
    profile = _fleet_profile_snapshot(_fleet_root() / "data")
    return (profile.get("active_slug") or os.getenv("FM_HERMES_PROJECT") or "clapart").strip()


def peek_fleet_backlog(project: str | None = None) -> dict[str, Any]:
    data_dir = _fleet_root() / "data"
    profile = _fleet_profile_snapshot(data_dir)
    slug = project or profile.get("active_slug")
    backlog = _fleet_backlog_snapshot(data_dir, slug)
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
    if os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return False
    lowered = (transcript or "").lower()
    return not any(w in lowered for w in ("confirm", "confirmed", "yes go ahead"))


def fleet_confirm_prompt(action: FleetVoiceAction) -> str:
    prompts = {
        "wake_firstmate": "To wake FirstMate and arm the fleet loop, say wake firstmate confirm.",
        "start_development": "To start development on a project, say start development on clapart confirm.",
        "run_next_backlog": "To dispatch the next backlog item to FirstMate, say run next backlog confirm.",
        "fleet_stop": "To stop the FirstMate fleet loop, say stop fleet confirm.",
    }
    return prompts.get(action, "Confirm yes on voice to proceed with this fleet action.")


async def invoke_fleet_trigger(
    message: str,
    *,
    project: str | None = None,
) -> dict[str, Any]:
    script = _trigger_script()
    slug = resolve_active_project(project)

    if _fleet_mock():
        return {
            "ok": True,
            "status": "mock",
            "message": message.strip(),
            "project": slug,
            "output": f"OK: mock fleet trigger — {message.strip()} @ {slug}",
        }

    if not script.is_file():
        return {
            "ok": False,
            "status": "trigger_script_missing",
            "path": str(script),
            "message": message.strip(),
            "project": slug,
        }

    env = os.environ.copy()
    env["FM_HERMES_PROJECT"] = slug
    env.setdefault("FIRSTMATE_CONTAINER", "firstmate-fleet")

    proc = await asyncio.create_subprocess_exec(
        "bash",
        str(script),
        *message.split(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "status": "dispatched" if ok else "failed",
        "exit_code": proc.returncode,
        "output": output,
        "message": message.strip(),
        "project": slug,
    }


async def fleet_trigger_from_voice(
    action: FleetVoiceAction,
    transcript: str,
    *,
    confirmed: bool = False,
) -> dict[str, Any]:
    if not confirmed and fleet_action_needs_confirm(transcript):
        return {
            "ok": False,
            "status": "confirmation_required",
            "action": action,
            "prompt": fleet_confirm_prompt(action),
        }

    project = extract_project_slug(transcript) or resolve_active_project()

    if action == "fleet_stop":
        result = await invoke_fleet_trigger("stop", project=project)
        spoken = (
            f"FirstMate fleet loop stopped on {project}."
            if result.get("ok")
            else f"Could not stop FirstMate fleet: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        return result

    if action == "wake_firstmate":
        result = await invoke_fleet_trigger("arm", project=project)
        spoken = (
            f"FirstMate fleet loop armed on {project}. Captain will pick up from the wake queue."
            if result.get("ok")
            else f"Could not wake FirstMate: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        return result

    if action == "run_next_backlog":
        item = next_backlog_item(project)
        if not item:
            return {
                "ok": False,
                "status": "empty_backlog",
                "action": action,
                "project": project,
                "spoken": plain_copy(
                    f"No queued backlog items for {project}. Say fleet status to hear the queue."
                ),
            }
        result = await invoke_fleet_trigger(f"work {item}", project=project)
        spoken = (
            f"Dispatched next backlog item {item} on {project} to the FirstMate captain."
            if result.get("ok")
            else f"Could not dispatch backlog item: {result.get('output', result.get('status'))}"
        )
        result["spoken"] = plain_copy(spoken)
        result["action"] = action
        result["task"] = item
        return result

    if action == "start_development":
        arm = await invoke_fleet_trigger("arm", project=project)
        if not arm.get("ok"):
            arm["spoken"] = plain_copy(
                f"Could not arm FirstMate on {project}: {arm.get('output', arm.get('status'))}"
            )
            arm["action"] = action
            return arm

        item = next_backlog_item(project)
        if item:
            work = await invoke_fleet_trigger(f"work {item}", project=project)
            if work.get("ok"):
                spoken = (
                    f"Development started on {project}. Fleet loop armed and captain dispatched "
                    f"next backlog item {item}."
                )
                work["spoken"] = plain_copy(spoken)
                work["action"] = action
                work["armed"] = True
                work["task"] = item
                return work
            spoken = (
                f"Fleet armed on {project} but work dispatch failed: "
                f"{work.get('output', work.get('status'))}"
            )
            arm["spoken"] = plain_copy(spoken)
            arm["action"] = action
            arm["armed"] = True
            return arm

        work = await invoke_fleet_trigger(
            f"work continue development on {project}",
            project=project,
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
        return work

    return {"ok": False, "status": "unknown_action", "action": action}