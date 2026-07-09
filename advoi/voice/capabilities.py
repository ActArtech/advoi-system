"""ADVoi operator catalog — what the control layer can do (voice + PWA)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from advoi.decision.frames import FRAMES
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import _fleet_profile_snapshot, _fleet_root

OperatorIntent = Literal[
    "capabilities",
    "firstmate_info",
    "github_info",
    "run_all",
    "dispatch_squads",
    "stop_agents",
    "restart_agents",
]


def _fleet_data_dir() -> Path:
    return _fleet_root() / "data"


def classify_operator_intent(transcript: str) -> OperatorIntent | None:
    """Meta commands that should not fall through to vague LLM chat."""
    text = (transcript or "").strip().lower()
    if not text:
        return None

    if any(
        p in text
        for p in (
            "what can you do",
            "what do you do",
            "what are you able",
            "your capabilities",
            "list commands",
            "voice commands",
            "operator list",
            "operators",
            "help me use",
            "how do i use advoi",
            "how do i use this",
        )
    ):
        return "capabilities"

    if any(
        p in text
        for p in (
            "dispatch all squads",
            "dispatch squads",
            "run all squads",
            "queue all squads",
        )
    ):
        return "dispatch_squads"

    if any(
        p in text
        for p in (
            "run all agents",
            "run all frames",
            "run everything",
            "full systems check",
            "check all systems",
            "refresh all agents",
        )
    ):
        return "run_all"

    if any(
        p in text
        for p in (
            "restart agents",
            "restart agent",
            "start agents",
            "start agent daemons",
            "resume agents",
            "bring agents back",
            "run agents again",
        )
    ):
        return "restart_agents"

    if any(
        p in text
        for p in (
            "stop agents",
            "stop agent",
            "pause agents",
            "pause agent daemons",
            "stop the system",
            "stop background agents",
            "halt agents",
        )
    ):
        return "stop_agents"

    if "github" in text or "git hub" in text:
        if any(w in text for w in ("access", "have", "repo", "repository", "read")):
            return "github_info"

    if any(
        p in text
        for p in (
            "firstmate",
            "first mate",
            "fleet captain",
            "do you use firstmate",
            "access to firstmate",
            "hermes fleet",
        )
    ):
        if "status" not in text and "pulse" not in text:
            return "firstmate_info"

    return None


def build_capabilities_payload() -> dict[str, Any]:
    """Structured operator catalog for API and PWA."""
    fleet = _fleet_profile_snapshot(_fleet_data_dir())
    voice_commands = [
        {
            "phrase": f.voice_prompt,
            "frame_id": f.id,
            "label": f.label,
            "agent_id": f.agent_id,
            "requires_confirmation": f.requires_confirmation,
        }
        for f in FRAMES
    ]

    operators = [
        {
            "id": "run_six",
            "label": "Run all 6 agents",
            "voice_phrases": ["run all agents", "full systems check"],
            "api": "POST /api/agents/run-six?refresh=true",
        },
        {
            "id": "dispatch_squads",
            "label": "Run 6 agents and dispatch all squads",
            "voice_phrases": ["dispatch all squads", "dispatch squads"],
            "api": "POST /api/agents/run-six?refresh=true&dispatch_squads=true",
        },
        {
            "id": "systems_pulse",
            "label": "Systems pulse",
            "voice_phrases": ["systems pulse", "portfolio pulse"],
            "frame_id": "systems_pulse",
        },
        {
            "id": "prewarm",
            "label": "Prewarm agent cache",
            "api": "POST /api/agents/prewarm",
        },
        {
            "id": "capabilities",
            "label": "List what ADVoi can do",
            "voice_phrases": ["what can you do", "list commands"],
        },
        {
            "id": "stop_agents",
            "label": "Pause background agent daemons",
            "voice_phrases": ["stop agents", "pause agents", "stop the system"],
            "api": "POST /api/agents/stop",
            "requires_confirmation": True,
        },
        {
            "id": "restart_agents",
            "label": "Restart agent daemons and prewarm",
            "voice_phrases": ["restart agents", "start agents again", "resume agents"],
            "api": "POST /api/agents/restart",
        },
    ]

    systems_access = {
        "firstmate_fleet": {
            "read": True,
            "write": False,
            "path": str(_fleet_root()),
            "configured": fleet.get("profile_found", False),
            "active_slug": fleet.get("active_slug"),
            "github_repo": fleet.get("github_repo"),
            "mode": fleet.get("mode"),
        },
        "hermes_memory": {
            "bridge": os.getenv("HINDSIGHT_BRIDGE", "mock"),
            "provider": os.getenv("MEMORY_PROVIDER", "hindsight"),
        },
        "aether_portfolio": {
            "portfolio_path": os.getenv("AETHER_PORTFOLIO_PATH", "data/aether/portfolio.json"),
        },
        "github": {
            "fleet_repo": fleet.get("github_repo"),
            "advoi_repo": "ActArtech/advoi-system",
            "read_only": True,
        },
    }

    return {
        "role": "voice-first executive control layer",
        "specialist_count": len(AGENTS),
        "frame_count": len(FRAMES),
        "voice_commands": voice_commands,
        "operators": operators,
        "systems_access": systems_access,
        "proactive_phrases": [
            "fleet status",
            "open briefs",
            "systems pulse",
            "memory health",
            "guardian status",
            "queue deep review",
            "what can you do",
        ],
    }


def spoken_capabilities_summary() -> str:
    """Definitive spoken answer for 'what can you do' — no LLM guessing."""
    payload = build_capabilities_payload()
    n = payload["specialist_count"]
    lines = [
        f"I am ADVoi, your voice control layer over {n} specialist agents and your portfolio stack.",
        "Say fleet status for FirstMate fleet read-only.",
        "Say open briefs for decision briefs from memory.",
        "Say systems pulse for fleet plus briefs in one pass.",
        "Say memory health or guardian status for infrastructure checks.",
        "Say queue deep review to queue desktop follow-up, then confirm yes.",
        "Say run all agents for a full parallel refresh.",
        "Say stop agents to pause background daemons, or restart agents to bring them back.",
    ]
    fleet = payload["systems_access"]["firstmate_fleet"]
    if fleet.get("configured"):
        slug = fleet.get("active_slug") or "unknown"
        lines.append(f"FirstMate fleet is connected read-only. Active venture is {slug}.")
    else:
        lines.append(
            "FirstMate fleet path is not configured on this host. Set FIRSTMATE_FLEET_PATH."
        )
    gh = payload["systems_access"]["github"].get("fleet_repo")
    if gh:
        lines.append(f"I can read the fleet GitHub repo {gh} from fleet profile. Code changes go through FirstMate, not ADVoi.")
    return " ".join(lines[:8])


def spoken_firstmate_access() -> str:
    fleet = _fleet_profile_snapshot(_fleet_data_dir())
    root = str(_fleet_root())
    if not fleet.get("profile_found"):
        return (
            f"FirstMate integration is read-only via {root}. "
            "Fleet profile is not found on this host yet. "
            "Say fleet status once the fleet tree is mounted, or check FIRSTMATE_FLEET_PATH on the server."
        )
    slug = fleet.get("active_slug") or "unknown"
    mode = fleet.get("mode") or "unknown"
    repo = fleet.get("github_repo") or "not set in profile"
    return (
        f"Yes. I have read-only access to FirstMate fleet at {root}. "
        f"Active slug is {slug}, mode {mode}, GitHub {repo}. "
        "I do not execute crew jobs from voice yet; I surface status and route frames. "
        "Say fleet status or systems pulse for a live read."
    )


def spoken_github_access() -> str:
    fleet = _fleet_profile_snapshot(_fleet_data_dir())
    fleet_repo = fleet.get("github_repo")
    parts = [
        "ADVoi does not push to GitHub. I read portfolio and fleet metadata only.",
        "ADVoi system code lives at ActArtech slash advoi-system on GitHub.",
    ]
    if fleet_repo:
        parts.append(f"FirstMate fleet profile points at {fleet_repo} for the active venture.")
    else:
        parts.append("Fleet GitHub repo is not set in fleet-profile.md on this host.")
    parts.append("Say fleet status to hear what the fleet is working on.")
    return " ".join(parts)