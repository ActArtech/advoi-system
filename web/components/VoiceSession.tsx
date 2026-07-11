"use client";

import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
} from "livekit-client";
import { stripEmDash } from "@/voice-interface/warmth";
import styles from "./VoiceSession.module.css";
import {
  classifyApiError,
  classifyConnectError,
  errorRecoveryModel,
  recoveryBeaconPayload,
  type ErrorRecoveryModel,
} from "./errorRecovery";
import {
  aetherGateChipModel,
  type AetherStatusPayload,
} from "./aetherGateChip";
import {
  latencyChipModel,
  type LatencyDiagnostics,
} from "./latencyChip";
import {
  confirmParityModel,
  type ConfirmParityModel,
} from "./confirmParity";
import {
  emitBeaconForUiEvent,
  emitPwaBeacon,
} from "./pwaBeacon";
import { PROJECT_SWITCH_EVENT } from "@/lib/portfolio/projectModel";
import {
  INITIAL_UI_SESSION,
  reduceUiSession,
  uiStateLabel,
  type UiSessionContext,
  type UiSessionEvent,
} from "./voiceSessionState";
import { BRIEFS_REFRESH_EVENT } from "./pwaBriefsSurface";
import { RUN_FRAME_EVENT } from "./pwaOnboarding";

type DecisionFrame = {
  id: string;
  label: string;
  agent_id: string;
  agent_name: string;
  requires_confirmation: boolean;
  voice_prompt: string;
};

type LastRun = {
  agent_id?: string;
  frame_id?: string;
  status?: string;
  spoken_summary?: string;
  timestamp?: number | string;
};

type AgentRow = {
  id: string;
  name: string;
  cached: boolean;
  frame_id?: string;
  last_run?: LastRun;
};

type VoiceDiagnostics = {
  ok: boolean;
  checks?: {
    agents?: number;
    frame_run_ms?: number;
  };
};

type CapabilitiesPayload = {
  specialist_count?: number;
  frame_count?: number;
  voice_commands?: { phrase: string; frame_id: string; label: string }[];
  operators?: { id: string; label: string; voice_phrases?: string[] }[];
  systems_access?: {
    firstmate_fleet?: { configured?: boolean; active_slug?: string; github_repo?: string };
    github?: { fleet_repo?: string; advoi_repo?: string };
  };
};

type FleetAction = "wake_firstmate" | "start_development" | "run_next_backlog" | "fleet_stop";

const FLEET_LABELS: Record<FleetAction, string> = {
  wake_firstmate: "Wake FirstMate",
  start_development: "Start dev",
  run_next_backlog: "Next backlog",
  fleet_stop: "Stop fleet",
};

const tokenEndpoint =
  process.env.NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT || "/api/livekit/token";
const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

const FRAME_SHORT: Record<string, string> = {
  fleet_status: "fleet",
  open_briefs: "briefs",
  queue_deep_review: "review",
  systems_pulse: "pulse",
  memory_health: "memory",
  guardian_status: "guardian",
};

function parseTimestamp(ts: number | string): number | null {
  if (typeof ts === "number") {
    return ts < 1e12 ? ts * 1000 : ts;
  }
  const parsed = Date.parse(ts);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatFreshness(lastRun?: LastRun, frameId?: string): string | null {
  if (!lastRun && !frameId) return null;

  const ts = lastRun?.timestamp;
  if (ts != null) {
    const ms = parseTimestamp(ts);
    if (ms != null) {
      const sec = Math.max(0, Math.floor((Date.now() - ms) / 1000));
      if (sec < 15) return "just now";
      if (sec < 60) return `${sec}s ago`;
      if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
      return `${Math.floor(sec / 86400)}d ago`;
    }
  }

  const fid = lastRun?.frame_id || frameId;
  if (fid) return FRAME_SHORT[fid] || fid;
  return "warm";
}

function attachRemoteAudio(track: { kind: Track.Kind; attach: () => HTMLMediaElement }) {
  if (track.kind !== Track.Kind.Audio) return;
  const el = track.attach();
  el.autoplay = true;
  document.body.appendChild(el);
}

export function VoiceSession() {
  const [ui, dispatchUiRaw] = useReducer(
    (ctx: UiSessionContext, event: UiSessionEvent) => reduceUiSession(ctx, event),
    INITIAL_UI_SESSION,
  );
  const state = ui.state;
  const voiceConnected = ui.voiceConnected;
  const [status, setStatus] = useState("Tap connect for voice, or tap a frame to test agents.");
  const [roomName, setRoomName] = useState("");
  const [frames, setFrames] = useState<DecisionFrame[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [activeFrame, setActiveFrame] = useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<string | null>(null);
  /** Guardian confirm panel — same copy for voice TTS and tap UI. */
  const [confirmUi, setConfirmUi] = useState<ConfirmParityModel | null>(null);
  const [voiceDiag, setVoiceDiag] = useState<VoiceDiagnostics | null>(null);
  const [latencyDiag, setLatencyDiag] = useState<LatencyDiagnostics | null>(null);
  const [aetherStatus, setAetherStatus] = useState<AetherStatusPayload | null>(null);
  const [micOn, setMicOn] = useState(false);
  const [typedLine, setTypedLine] = useState("");
  const [capabilities, setCapabilities] = useState<CapabilitiesPayload | null>(null);
  const [operatorBusy, setOperatorBusy] = useState(false);
  const [pendingFleet, setPendingFleet] = useState<FleetAction | null>(null);
  const [voiceSessionId] = useState(() => `pwa-${Date.now()}`);
  /** Recovery panel for UI `error` state (mic / LiveKit / API). */
  const [errorRecovery, setErrorRecovery] = useState<ErrorRecoveryModel | null>(null);
  /** Last failed frame id for Retry on api_frame recovery. */
  const [lastFailedFrameId, setLastFailedFrameId] = useState<string | null>(null);

  /** State-machine dispatch with PEL thin-beacon side effects (no third-party SDK). */
  const dispatchUi = useCallback(
    (event: UiSessionEvent, extra?: Record<string, unknown>) => {
      dispatchUiRaw(event);
      emitBeaconForUiEvent(apiBase, event, {
        session_id: voiceSessionId,
        payload: extra,
      });
    },
    [voiceSessionId],
  );

  const clearErrorRecovery = useCallback(() => {
    setErrorRecovery(null);
    setLastFailedFrameId(null);
  }, []);

  const surfaceRecovery = useCallback(
    (
      model: ErrorRecoveryModel,
      uiEvent: UiSessionEvent,
      extra?: Record<string, unknown>,
    ) => {
      setErrorRecovery(model);
      dispatchUi(uiEvent, {
        ...recoveryBeaconPayload(model),
        ...(extra || {}),
      });
      setStatus(model.message);
    },
    [dispatchUi],
  );

  const room = useMemo(
    () =>
      new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      }),
    [],
  );

  const loadLatency = useCallback(() => {
    fetch(`${apiBase}/diagnostics/latency`)
      .then((r) => {
        if (!r.ok) {
          setLatencyDiag({ ok: false, error: `HTTP ${r.status}` });
          return null;
        }
        return r.json();
      })
      .then((data) => {
        if (data) setLatencyDiag(data as LatencyDiagnostics);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "fetch failed";
        setLatencyDiag({ ok: false, error: message });
      });
  }, []);

  const loadAetherStatus = useCallback(() => {
    fetch(`${apiBase}/aether/status`)
      .then((r) => {
        if (!r.ok) {
          setAetherStatus({ ok: false, error: `HTTP ${r.status}` });
          return null;
        }
        return r.json();
      })
      .then((data) => {
        if (data) setAetherStatus(data as AetherStatusPayload);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : "fetch failed";
        setAetherStatus({ ok: false, error: message });
      });
  }, []);

  const loadDiagnostics = useCallback(() => {
    fetch(`${apiBase}/diagnostics/voice`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setVoiceDiag(data as VoiceDiagnostics | null))
      .catch(() => setVoiceDiag(null));

    loadLatency();
    loadAetherStatus();
  }, [loadLatency, loadAetherStatus]);

  const loadAgents = useCallback(() => {
    fetch(`${apiBase}/agents`)
      .then((r) => r.json())
      .then((data) => {
        const rows = (data.agents || []).map(
          (a: {
            id: string;
            name: string;
            cached?: boolean;
            frame_id?: string;
            last_run?: LastRun;
          }) => ({
            id: a.id,
            name: a.name,
            cached: Boolean(a.cached),
            frame_id: a.frame_id,
            last_run: a.last_run,
          }),
        );
        setAgents(rows);
      })
      .catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    fetch(`${apiBase}/frames`)
      .then((r) => r.json())
      .then((data) => setFrames(data.frames || []))
      .catch(() => setFrames([]));
    fetch(`${apiBase}/capabilities`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setCapabilities(data as CapabilitiesPayload | null))
      .catch(() => setCapabilities(null));
    loadAgents();
    loadDiagnostics();
    const agentsT = setInterval(loadAgents, 30000);
    const diagT = setInterval(loadDiagnostics, 60000);
    return () => {
      clearInterval(agentsT);
      clearInterval(diagT);
    };
  }, [loadAgents, loadDiagnostics]);

  useEffect(() => {
    const onState = (s: ConnectionState) => {
      if (s === ConnectionState.Connected) {
        // Reducer preserves frame_running / confirm_pending when voice comes up mid-work.
        // CONNECT_OK → pwa_connect beacon via dispatchUi.
        dispatchUi({ type: "CONNECT_OK" }, { transport: "livekit" });
        setStatus((prev) =>
          prev.includes("working") || prev.includes("Confirm")
            ? prev
            : "Connected. Speak or tap a decision frame.",
        );
      } else if (s === ConnectionState.Connecting) {
        dispatchUi({ type: "CONNECT_START" });
        setStatus("Connecting to LiveKit...");
      } else if (s === ConnectionState.Disconnected) {
        dispatchUi({ type: "DISCONNECT" });
        setStatus("Disconnected. Frames still work in text mode.");
        setPendingConfirm(null);
        setPendingFleet(null);
        setConfirmUi(null);
      }
    };

    const onMediaError = (error: Error) => {
      setMicOn(false);
      const model = errorRecoveryModel({
        kind: "mic_denied",
        detail: error.message,
      });
      setErrorRecovery(model);
      dispatchUi(
        { type: "ERROR" },
        { ...recoveryBeaconPayload(model), source: "media" },
      );
      setStatus(model.message);
    };

    room.on(RoomEvent.ConnectionStateChanged, onState);
    room.on(RoomEvent.TrackSubscribed, attachRemoteAudio);
    room.on(RoomEvent.MediaDevicesError, onMediaError);
    room.on(RoomEvent.LocalTrackPublished, (pub) => {
      if (pub.kind === Track.Kind.Audio) setMicOn(true);
    });
    room.on(RoomEvent.LocalTrackUnpublished, (pub) => {
      if (pub.kind === Track.Kind.Audio) setMicOn(false);
    });

    return () => {
      room.off(RoomEvent.ConnectionStateChanged, onState);
      room.off(RoomEvent.TrackSubscribed, attachRemoteAudio);
      room.off(RoomEvent.MediaDevicesError, onMediaError);
      room.disconnect();
    };
  }, [dispatchUi, room]);

  const publishSpeak = useCallback(
    async (text: string) => {
      // Speak while voice transport is up, including during frame_running / confirm_pending.
      if (!voiceConnected) return;
      await room.startAudio();
      const payload = new TextEncoder().encode(
        JSON.stringify({ type: "speak", text: stripEmDash(text) }),
      );
      await room.localParticipant.publishData(payload, { reliable: true });
    },
    [room, voiceConnected],
  );

  const runFrame = useCallback(
    async (frameId: string, confirmed = false, refresh = false) => {
      setActiveFrame(frameId);
      clearErrorRecovery();
      if (confirmed) {
        emitPwaBeacon(apiBase, {
          type: "confirm_accept",
          session_id: voiceSessionId,
          payload: { target: "frame", frame_id: frameId },
          guardian_status: "allowed",
        });
      }
      dispatchUi(
        { type: "FRAME_START" },
        { target: "frame", frame_id: frameId, confirmed },
      );
      const frame = frames.find((f) => f.id === frameId);
      setStatus(`${frame?.agent_name || "Agent"} working...`);

      try {
        const qs = refresh ? "?refresh=true" : "";
        const resp = await fetch(`${apiBase}/frames/${frameId}/run${qs}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmed, refresh }),
        });
        if (!resp.ok) {
          const err = new Error(`Frame returned ${resp.status}`);
          const classified = classifyApiError(err, {
            httpStatus: resp.status,
            target: frameId,
          });
          setLastFailedFrameId(frameId);
          surfaceRecovery(
            errorRecoveryModel(classified),
            { type: "ERROR" },
            { target: "frame", frame_id: frameId },
          );
          return;
        }
        const data = await resp.json();

        if (data.status === "confirmation_required") {
          setPendingConfirm(frameId);
          const model = confirmParityModel({
            prompt: typeof data.prompt === "string" ? data.prompt : null,
            spoken_summary:
              typeof data.spoken_summary === "string" ? data.spoken_summary : null,
            spoken: typeof data.spoken === "string" ? data.spoken : null,
            targetKind: "frame",
            targetId: frameId,
          });
          setConfirmUi(model);
          dispatchUi(
            { type: "CONFIRMATION_REQUIRED" },
            {
              target: "frame",
              frame_id: frameId,
              confirm_copy: model.copy,
              path: "tap",
            },
          );
          // Identical copy for status (tap) and TTS (voice) — moat 7.4 parity.
          setStatus(model.copy);
          await publishSpeak(model.copy);
          return;
        }

        setPendingConfirm(null);
        setConfirmUi(null);
        clearErrorRecovery();
        dispatchUi({ type: "FRAME_OK" });
        const spoken = stripEmDash(data.spoken_summary as string);
        setStatus(
          voiceConnected ? spoken : `${spoken} Connect voice to hear TTS.`,
        );
        await publishSpeak(spoken);
        loadAgents();
        // Refresh SLA chip without full page reload (ship #2).
        loadLatency();
        // Home briefs surface: immediate reload after queue / open-briefs frames.
        if (frameId === "queue_deep_review" || frameId === "open_briefs") {
          window.dispatchEvent(new CustomEvent(BRIEFS_REFRESH_EVENT));
        }
      } catch (err) {
        const classified = classifyApiError(err, { target: frameId });
        setLastFailedFrameId(frameId);
        surfaceRecovery(
          errorRecoveryModel(classified),
          { type: "ERROR" },
          { target: "frame", frame_id: frameId },
        );
      } finally {
        setActiveFrame(null);
      }
    },
    [
      apiBase,
      clearErrorRecovery,
      dispatchUi,
      frames,
      loadAgents,
      loadLatency,
      publishSpeak,
      surfaceRecovery,
      voiceConnected,
      voiceSessionId,
    ],
  );

  // Home onboarding morning-pulse CTA (and any future home CTAs) dispatch this event.
  useEffect(() => {
    const onRunFrame = (ev: Event) => {
      const detail = (ev as CustomEvent<{ frameId?: string; refresh?: boolean }>).detail;
      const frameId = detail?.frameId;
      if (!frameId || typeof frameId !== "string") return;
      void runFrame(frameId, false, Boolean(detail?.refresh));
    };
    window.addEventListener(RUN_FRAME_EVENT, onRunFrame);
    return () => window.removeEventListener(RUN_FRAME_EVENT, onRunFrame);
  }, [runFrame]);

  const speakFromIntent = useCallback(
    async (transcript: string) => {
      const text = transcript.trim();
      if (!text) return;
      clearErrorRecovery();
      dispatchUi({ type: "FRAME_START" }, { target: "intent" });
      setStatus("Understanding...");
      try {
        const intentResp = await fetch(`${apiBase}/voice/intent`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transcript: text, preview: true }),
        });
        if (intentResp.ok) {
          const data = await intentResp.json();
          const opPreview = data.operator_preview as
            | {
                spoken?: string;
                action?: string;
                pending_operator?: string;
                agents_used?: string[];
              }
            | undefined;
          if (opPreview?.spoken) {
            if (opPreview.action === "confirmation_required") {
              const pending = opPreview.pending_operator;
              const isFleet =
                pending === "wake_firstmate" ||
                pending === "start_development" ||
                pending === "run_next_backlog" ||
                pending === "fleet_stop";
              if (isFleet && pending) {
                setPendingFleet(pending as FleetAction);
              }
              const model = confirmParityModel({
                spoken: opPreview.spoken,
                targetKind: isFleet ? "fleet" : "operator",
                targetId: pending || "operator",
                acceptTranscript: pending
                  ? `${String(pending).replace(/_/g, " ")} confirm`
                  : /\bstop agents\b/i.test(opPreview.spoken)
                    ? "stop agents confirm"
                    : "yes",
              });
              setConfirmUi(model);
              dispatchUi(
                { type: "CONFIRMATION_REQUIRED" },
                {
                  target: isFleet ? "fleet" : "operator",
                  pending: pending || null,
                  confirm_copy: model.copy,
                  path: "voice",
                },
              );
              setStatus(model.copy);
              await publishSpeak(model.copy);
              return;
            }
            setPendingFleet(null);
            setConfirmUi(null);
            if (data.confirmed || /\bconfirm\b/i.test(text)) {
              emitPwaBeacon(apiBase, {
                type: "confirm_accept",
                session_id: voiceSessionId,
                payload: { target: "operator", action: opPreview.action },
                guardian_status: "allowed",
              });
            }
            dispatchUi({ type: "FRAME_OK" });
            if (opPreview.action === "run_all" || opPreview.action === "dispatch_squads") {
              void loadAgents();
            }
            const spoken = stripEmDash(opPreview.spoken);
            const agentNote =
              opPreview.agents_used && opPreview.agents_used.length > 0
                ? ` (${opPreview.agents_used.length} agents)`
                : "";
            setStatus(spoken + agentNote);
            await publishSpeak(spoken);
            return;
          }
          const projectAction = data.action as string | undefined;
          const ventureId = data.venture_id as string | undefined;
          if (
            ventureId &&
            (projectAction === "switch_project" || projectAction === "activate_function")
          ) {
            const ventureName = data.venture_name as string | undefined;
            const functionId = data.function_id as string | undefined;
            const frameId = data.frame_id as string | undefined;
            window.dispatchEvent(
              new CustomEvent(PROJECT_SWITCH_EVENT, {
                detail: {
                  ventureId,
                  ventureName,
                  functionId,
                  frameId,
                  source: "voice",
                },
              }),
            );
            const preview = data.preview?.spoken_summary as string | undefined;
            const spoken =
              preview ??
              (ventureName
                ? `Switched to ${ventureName}.`
                : `Switched to ${ventureId}.`);
            setConfirmUi(null);
            setStatus(stripEmDash(spoken));
            await publishSpeak(spoken);
            dispatchUi({ type: "FRAME_OK" });
            if (frameId && preview) {
              void loadAgents();
            }
            return;
          }
          const preview = data.preview?.spoken_summary as string | undefined;
          const frameId = data.frame_id as string | undefined;
          if (preview) {
            if (data.preview?.status === "confirmation_required" && frameId) {
              setPendingConfirm(frameId);
              const model = confirmParityModel({
                spoken_summary: preview,
                prompt:
                  typeof data.preview?.prompt === "string"
                    ? data.preview.prompt
                    : null,
                targetKind: "frame",
                targetId: frameId,
              });
              setConfirmUi(model);
              dispatchUi(
                { type: "CONFIRMATION_REQUIRED" },
                {
                  target: "frame",
                  frame_id: frameId,
                  confirm_copy: model.copy,
                  path: "voice",
                },
              );
              setStatus(model.copy);
              await publishSpeak(model.copy);
            } else {
              setConfirmUi(null);
              setStatus(stripEmDash(preview));
              await publishSpeak(preview);
              dispatchUi({ type: "FRAME_OK" });
            }
            return;
          }
          if (frameId && data.action === "frame") {
            await runFrame(
              frameId,
              Boolean(data.confirmed),
              frameId === "fleet_status" || frameId === "systems_pulse",
            );
            return;
          }
        }
        const resp = await fetch(`${apiBase}/voice/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transcript: text, session_id: voiceSessionId }),
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.action === "confirmation_required") {
            const pending = data.pending_operator as string | undefined;
            const isFleet =
              pending === "wake_firstmate" ||
              pending === "start_development" ||
              pending === "run_next_backlog" ||
              pending === "fleet_stop";
            if (isFleet && pending) {
              setPendingFleet(pending as FleetAction);
            }
            const model = confirmParityModel({
              prompt: typeof data.prompt === "string" ? data.prompt : null,
              spoken: typeof data.spoken === "string" ? data.spoken : null,
              targetKind: isFleet ? "fleet" : "operator",
              targetId: pending || "operator",
              acceptTranscript: pending
                ? `${String(pending).replace(/_/g, " ")} confirm`
                : "yes",
            });
            setConfirmUi(model);
            dispatchUi(
              { type: "CONFIRMATION_REQUIRED" },
              {
                target: isFleet ? "fleet" : "operator",
                pending: pending || null,
                confirm_copy: model.copy,
                path: "voice",
              },
            );
            setStatus(model.copy);
            await publishSpeak(model.copy);
            return;
          }
          setPendingFleet(null);
          setConfirmUi(null);
          clearErrorRecovery();
          dispatchUi({ type: "FRAME_OK" });
          if (data.action === "run_all" || data.action === "dispatch_squads") {
            void loadAgents();
          }
          const spoken = stripEmDash(String(data.spoken || ""));
          const agentsUsed = data.agents_used as string[] | undefined;
          const agentNote =
            agentsUsed && agentsUsed.length > 0 ? ` (${agentsUsed.length} agents)` : "";
          setStatus(spoken + agentNote);
          await publishSpeak(spoken);
        } else {
          const classified = classifyApiError(new Error(`Intent returned ${resp.status}`), {
            httpStatus: resp.status,
            target: "intent",
          });
          surfaceRecovery(
            errorRecoveryModel(classified),
            { type: "ERROR" },
            { target: "intent" },
          );
        }
      } catch (err) {
        const classified = classifyApiError(err, { target: "intent" });
        surfaceRecovery(
          errorRecoveryModel(classified),
          { type: "ERROR" },
          { target: "intent" },
        );
      }
    },
    [clearErrorRecovery, dispatchUi, loadAgents, publishSpeak, runFrame, surfaceRecovery, voiceSessionId],
  );

  const runFleetOperator = useCallback(
    async (action: FleetAction, confirmed = false) => {
      if (operatorBusy) return;
      setOperatorBusy(true);
      clearErrorRecovery();
      if (confirmed) {
        emitPwaBeacon(apiBase, {
          type: "confirm_accept",
          session_id: voiceSessionId,
          payload: { target: "fleet", action },
          guardian_status: "allowed",
        });
      }
      dispatchUi(
        { type: "FRAME_START" },
        { target: "fleet", action, confirmed },
      );
      const project = capabilities?.systems_access?.firstmate_fleet?.active_slug;
      const label = FLEET_LABELS[action];
      setStatus(confirmed ? `${label}...` : `Confirm ${label.toLowerCase()}...`);
      try {
        const transcript =
          action === "start_development"
            ? `start development${project ? ` on ${project}` : ""}${confirmed ? " confirm" : ""}`
            : `${action.replace(/_/g, " ")}${confirmed ? " confirm" : ""}`;
        const resp = await fetch(`${apiBase}/fleet/trigger`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            confirmed,
            project,
            transcript,
          }),
        });
        if (!resp.ok) throw new Error(`Fleet trigger returned ${resp.status}`);
        const data = await resp.json();
        if (data.status === "confirmation_required") {
          setPendingFleet(action);
          const model = confirmParityModel({
            prompt: typeof data.prompt === "string" ? data.prompt : null,
            spoken: typeof data.spoken === "string" ? data.spoken : null,
            spoken_summary:
              typeof data.spoken_summary === "string" ? data.spoken_summary : null,
            targetKind: "fleet",
            targetId: action,
          });
          setConfirmUi(model);
          dispatchUi(
            { type: "CONFIRMATION_REQUIRED" },
            {
              target: "fleet",
              action,
              confirm_copy: model.copy,
              path: "tap",
            },
          );
          setStatus(model.copy);
          await publishSpeak(model.copy);
          return;
        }
        setPendingFleet(null);
        setConfirmUi(null);
        clearErrorRecovery();
        dispatchUi({ type: "FRAME_OK" });
        const spoken = stripEmDash(String(data.spoken || `${label} completed.`));
        setStatus(spoken);
        await publishSpeak(spoken);
        loadAgents();
      } catch (err) {
        const classified = classifyApiError(err, { target: action });
        surfaceRecovery(
          errorRecoveryModel(classified),
          { type: "ERROR" },
          { target: "fleet", action },
        );
      } finally {
        setOperatorBusy(false);
      }
    },
    [
      apiBase,
      capabilities,
      clearErrorRecovery,
      dispatchUi,
      loadAgents,
      operatorBusy,
      publishSpeak,
      surfaceRecovery,
      voiceSessionId,
    ],
  );

  const submitTypedLine = useCallback(() => {
    const line = typedLine.trim();
    if (!line) return;
    setTypedLine("");
    void speakFromIntent(line);
  }, [speakFromIntent, typedLine]);

  const runOperator = useCallback(
    async (
      kind:
        | "run_six"
        | "run_six_squads"
        | "prewarm"
        | "capabilities"
        | "stop_agents"
        | "restart_agents",
    ) => {
      if (operatorBusy) return;
      setOperatorBusy(true);
      clearErrorRecovery();
      try {
        if (kind === "capabilities") {
          await speakFromIntent("what can you do");
          return;
        }
        dispatchUi({ type: "FRAME_START" }, { target: "operator", kind });
        if (kind === "stop_agents") {
          setStatus("Pausing background agent daemons...");
          const resp = await fetch(`${apiBase}/agents/stop`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ confirmed: true }),
          });
          const data = await resp.json();
          const spoken = stripEmDash(
            String(data.spoken_summary || "Background agents paused."),
          );
          setStatus(spoken);
          await publishSpeak(spoken);
          dispatchUi({ type: "FRAME_OK" });
          loadAgents();
          loadLatency();
          return;
        }
        if (kind === "restart_agents") {
          setStatus("Restarting agent daemons...");
          const resp = await fetch(`${apiBase}/agents/restart`, { method: "POST" });
          const data = await resp.json();
          const spoken = stripEmDash(
            String(data.spoken_summary || "Agents restarted."),
          );
          setStatus(spoken);
          await publishSpeak(spoken);
          dispatchUi({ type: "FRAME_OK" });
          loadAgents();
          loadLatency();
          return;
        }
        if (kind === "prewarm") {
          setStatus("Prewarming all specialist agents...");
          const resp = await fetch(`${apiBase}/agents/prewarm`, { method: "POST" });
          if (!resp.ok) throw new Error(`Prewarm returned ${resp.status}`);
          const data = await resp.json();
          const spoken = stripEmDash(
            String(data.spoken_summary || "Agents prewarmed. Say systems pulse for a full read."),
          );
          setStatus(spoken);
          await publishSpeak(spoken);
          dispatchUi({ type: "FRAME_OK" });
          loadAgents();
          loadLatency();
          return;
        }
        const dispatchSquads = kind === "run_six_squads";
        setStatus(
          dispatchSquads
            ? "Running all six agents and dispatching squads..."
            : "Running all six specialist agents...",
        );
        const qs = new URLSearchParams({
          refresh: "true",
          confirmed: "true",
          ...(dispatchSquads ? { dispatch_squads: "true" } : {}),
        });
        const resp = await fetch(`${apiBase}/agents/run-six?${qs}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        if (!resp.ok) throw new Error(`Run-six returned ${resp.status}`);
        const data = await resp.json();
        let spoken = stripEmDash(String(data.spoken_summary || "All agents finished."));
        if (data.squads?.dispatched != null) {
          spoken += ` Squads ${data.squads.dispatched}/${data.squads.total} dispatched.`;
        }
        setStatus(spoken);
        await publishSpeak(spoken);
        clearErrorRecovery();
        dispatchUi({ type: "FRAME_OK" });
        loadAgents();
        // Run-six / prewarm complete — refresh SLA chip (frame_run_ms + run_six_ms).
        loadLatency();
      } catch (err) {
        const classified = classifyApiError(err, { target: kind });
        surfaceRecovery(
          errorRecoveryModel(classified),
          { type: "ERROR" },
          { target: "operator", kind },
        );
      } finally {
        setOperatorBusy(false);
      }
    },
    [
      apiBase,
      clearErrorRecovery,
      dispatchUi,
      loadAgents,
      loadLatency,
      operatorBusy,
      publishSpeak,
      speakFromIntent,
      surfaceRecovery,
    ],
  );

  const connect = useCallback(async () => {
    clearErrorRecovery();
    dispatchUi({ type: "CONNECT_START" });
    setStatus("Requesting microphone access...");
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("This browser does not support microphone capture.");
      }
      await navigator.mediaDevices.getUserMedia({ audio: true });

      setStatus("Requesting LiveKit token...");
      const resp = await fetch(tokenEndpoint, { method: "POST" });
      if (!resp.ok) {
        const status = resp.status;
        const tokenErr =
          status === 401 || status === 403 || status === 503
            ? stripEmDash(
                `Token failed (${status}). Check LiveKit API keys and that the advoi-voice container is running.`,
              )
            : `Token endpoint returned ${status}`;
        const classified = classifyConnectError(new Error(tokenErr), {
          httpStatus: status,
        });
        // Token failures are LiveKit path, not mic.
        surfaceRecovery(
          errorRecoveryModel({ ...classified, kind: "livekit_connect" }),
          { type: "CONNECT_FAIL" },
          { source: "token", status },
        );
        return;
      }
      const data = await resp.json();
      setRoomName(data.room_name || "");

      await room.connect(data.url, data.token);
      await room.startAudio();
      const micPub = await room.localParticipant.setMicrophoneEnabled(true);
      if (!micPub) {
        const classified = classifyConnectError(
          new Error("Microphone is blocked. Allow mic for this site and tap Connect again."),
        );
        surfaceRecovery(
          errorRecoveryModel(classified),
          { type: "CONNECT_FAIL" },
          { source: "mic" },
        );
        return;
      }
      setMicOn(true);
      room.remoteParticipants.forEach((participant) => {
        participant.audioTrackPublications.forEach((pub) => {
          if (pub.track) attachRemoteAudio(pub.track);
        });
      });
      clearErrorRecovery();
      dispatchUi({ type: "CONNECT_OK" }, { room_name: data.room_name || "" });
      setStatus(
        `Joined ${data.room_name}. Mic on. Say fleet status, systems pulse, memory health, guardian status, or what can you do.`,
      );
    } catch (err) {
      const classified = classifyConnectError(err);
      surfaceRecovery(
        errorRecoveryModel(classified),
        { type: "CONNECT_FAIL" },
        { source: classified.kind },
      );
    }
  }, [clearErrorRecovery, dispatchUi, room, surfaceRecovery]);

  const disconnect = useCallback(async () => {
    await room.localParticipant.setMicrophoneEnabled(false);
    await room.disconnect();
    clearErrorRecovery();
    dispatchUi({ type: "DISCONNECT" });
    setMicOn(false);
    setStatus("Session ended. Frames still work in text mode.");
    setPendingConfirm(null);
    setPendingFleet(null);
    setConfirmUi(null);
  }, [clearErrorRecovery, dispatchUi, room]);

  const retryFromRecovery = useCallback(() => {
    const kind = errorRecovery?.kind;
    // Only re-run frames we tracked via lastFailedFrameId (not fleet/intent/operator).
    if (kind === "api_frame" && lastFailedFrameId) {
      const frameId = lastFailedFrameId;
      clearErrorRecovery();
      dispatchUi({ type: "RESET_IDLE" });
      void runFrame(frameId, false, false);
      return;
    }
    if (kind === "mic_denied" || kind === "livekit_connect") {
      void connect();
      return;
    }
    // Intent/fleet/operator API fail or generic — clear shell so user can act again.
    clearErrorRecovery();
    dispatchUi({ type: "RESET_IDLE" });
    setStatus(
      voiceConnected
        ? "Ready again. Tap a frame or speak a command."
        : "Ready again. Tap Connect voice or a decision frame.",
    );
  }, [
    clearErrorRecovery,
    connect,
    dispatchUi,
    errorRecovery,
    lastFailedFrameId,
    runFrame,
    voiceConnected,
  ]);

  const dismissRecovery = useCallback(() => {
    clearErrorRecovery();
    dispatchUi({ type: "RESET_IDLE" });
    setStatus(
      voiceConnected
        ? "Error dismissed. Speak or tap a decision frame."
        : "Error dismissed. Frames still work in text mode.",
    );
  }, [clearErrorRecovery, dispatchUi, voiceConnected]);

  const onFrameClick = (frameId: string, ev: React.MouseEvent) => {
    const refresh = ev.shiftKey || frameId === "fleet_status" && ev.detail === 2;
    if (pendingConfirm === frameId) {
      void runFrame(frameId, true, refresh);
      return;
    }
    void runFrame(frameId, false, refresh);
  };

  /** Explicit Confirm button — same accept path as re-tap / voice "yes". */
  const acceptConfirm = useCallback(() => {
    if (!confirmUi) return;
    if (confirmUi.targetKind === "frame") {
      void runFrame(confirmUi.targetId, true, false);
      return;
    }
    if (confirmUi.targetKind === "fleet") {
      void runFleetOperator(confirmUi.targetId as FleetAction, true);
      return;
    }
    const line = confirmUi.acceptTranscript || "yes";
    void speakFromIntent(line);
  }, [confirmUi, runFleetOperator, runFrame, speakFromIntent]);

  const agentsReady = agents.filter((a) => a.cached).length;
  const agentsTotal = agents.length || voiceDiag?.checks?.agents;
  const slaChip = latencyChipModel(latencyDiag);
  const gateChip = aetherGateChipModel(aetherStatus);
  const expectedFrames = capabilities?.frame_count ?? 6;
  const deployStale = frames.length > 0 && frames.length < expectedFrames;
  const fleetAccess = capabilities?.systems_access?.firstmate_fleet;

  const stateLabel = uiStateLabel(state);

  return (
    <section className={styles.panel} data-ui-state={state}>
      <div className={styles.statusRow}>
        <div className={styles.chipGroup}>
          <span
            className={`${styles.stateChip} ${styles[state]}`}
            data-testid="ui-state-chip"
            data-state={state}
            title={`UI state: ${state}`}
          >
            <span className={`${styles.dot} ${styles[state]}`} aria-hidden />
            <span className={styles.stateChipLabel}>{stateLabel}</span>
          </span>
          <span
            className={`${styles.latencyChip} ${styles[slaChip.tone]}`}
            data-testid="sla-latency-chip"
            data-tone={slaChip.tone}
            data-available={slaChip.available ? "true" : "false"}
            data-sla-ok={
              slaChip.slaOk === null ? "unknown" : slaChip.slaOk ? "true" : "false"
            }
            data-frame-ms={
              slaChip.frameRunMs != null ? String(slaChip.frameRunMs) : ""
            }
            data-run-six-ms={
              slaChip.runSixMs != null ? String(slaChip.runSixMs) : ""
            }
            title={slaChip.title}
            aria-label={slaChip.title}
          >
            {slaChip.label}
          </span>
          <span
            className={`${styles.latencyChip} ${styles[gateChip.tone]}`}
            data-testid="aether-gate-chip"
            data-tone={gateChip.tone}
            data-available={gateChip.available ? "true" : "false"}
            data-verdict={gateChip.verdict ?? ""}
            data-active-slug={gateChip.activeSlug ?? ""}
            data-found={gateChip.found ? "true" : "false"}
            title={gateChip.title}
            aria-label={gateChip.title}
          >
            {gateChip.label}
          </span>
        </div>
        <p className={styles.status} role="status" aria-live="polite">
          {status}
        </p>
      </div>
      {roomName ? <p className={styles.meta}>Room: {roomName}</p> : null}

      {voiceDiag || agentsTotal != null ? (
        <div className={styles.systemHealth} aria-label="System health">
          {voiceDiag ? (
            <span
              className={`${styles.healthItem} ${voiceDiag.ok ? styles.healthOk : styles.healthWarn}`}
            >
              Voice: {voiceDiag.ok ? "ready" : "not ready"}
            </span>
          ) : null}
          {agentsTotal != null ? (
            <span className={styles.healthItem}>
              Agents: {agents.length > 0 ? `${agentsReady}/${agentsTotal}` : `?/${agentsTotal}`}
            </span>
          ) : null}
        </div>
      ) : null}

      {deployStale ? (
        <p className={styles.deployWarn}>
          API shows {frames.length} of {expectedFrames} decision frames. Redeploy staging (
          <code>staging-redeploy.sh</code>) for Options D-F and Aether.
        </p>
      ) : null}

      {fleetAccess?.configured ? (
        <p className={styles.meta}>
          FirstMate: {fleetAccess.active_slug || "connected"}
          {fleetAccess.github_repo ? ` · ${fleetAccess.github_repo}` : ""}
        </p>
      ) : null}

      {voiceConnected ? (
        <p className={styles.intentHint}>
          <span className={`${styles.micBadge} ${micOn ? styles.micOn : styles.micOff}`}>
            Mic {micOn ? "on" : "off"}
          </span>
          {" "}Voice: fleet status, wake firstmate confirm, start development confirm, run next backlog confirm,
          stop fleet confirm, systems pulse, memory health, guardian status, run all agents, what can you do.
          Say yes after a confirm prompt. Type below if mic fails.
        </p>
      ) : null}

      {state === "confirm_pending" && confirmUi ? (
        <div
          className={styles.confirmBanner}
          role="alert"
          data-testid="confirm-pending"
          data-confirm-target={confirmUi.targetKind}
          data-confirm-id={confirmUi.targetId}
        >
          <p className={styles.confirmBannerTitle}>{confirmUi.title}</p>
          <p className={styles.confirmCopy} data-testid="confirm-copy">
            {confirmUi.copy}
          </p>
          <div className={styles.confirmActions}>
            <button
              type="button"
              className={styles.confirmBtn}
              data-testid="confirm-accept"
              disabled={Boolean(activeFrame) || operatorBusy}
              onClick={acceptConfirm}
            >
              {confirmUi.buttonLabel}
            </button>
          </div>
        </div>
      ) : state === "confirm_pending" ? (
        <p className={styles.confirmBanner} role="alert" data-testid="confirm-pending">
          Confirmation required — tap Confirm or say yes.
        </p>
      ) : null}

      {state === "error" && errorRecovery ? (
        <div
          className={styles.errorRecovery}
          role="alert"
          data-testid="error-recovery"
          data-recovery-kind={errorRecovery.kind}
          data-recovery-status={
            errorRecovery.status != null ? String(errorRecovery.status) : ""
          }
        >
          <p className={styles.errorRecoveryTitle}>{errorRecovery.title}</p>
          <p className={styles.errorRecoveryMsg}>{errorRecovery.message}</p>
          <div className={styles.errorRecoveryActions}>
            {errorRecovery.showRetry ? (
              <button
                type="button"
                className={styles.errorRetryBtn}
                data-testid="error-recovery-retry"
                onClick={retryFromRecovery}
              >
                {errorRecovery.retryLabel}
              </button>
            ) : null}
            {errorRecovery.showPathC ? (
              <a
                className={styles.errorPathCLink}
                href={errorRecovery.pathCHref}
                data-testid="error-recovery-path-c"
              >
                {errorRecovery.pathCLabel}
              </a>
            ) : null}
            <button
              type="button"
              className={styles.errorDismissBtn}
              data-testid="error-recovery-dismiss"
              onClick={dismissRecovery}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <div className={styles.operatorBar} aria-label="Operator controls">
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runOperator("run_six")}
        >
          Run all 6
        </button>
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runOperator("run_six_squads")}
        >
          Dispatch squads
        </button>
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runFrame("systems_pulse", false, true)}
        >
          Systems pulse
        </button>
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runOperator("prewarm")}
        >
          Prewarm
        </button>
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runOperator("capabilities")}
        >
          What can you do
        </button>
        <button
          type="button"
          className={`${styles.opBtn} ${styles.opBtnDanger}`}
          disabled={operatorBusy}
          onClick={() => void runOperator("stop_agents")}
        >
          Stop agents
        </button>
        <button
          type="button"
          className={styles.opBtn}
          disabled={operatorBusy}
          onClick={() => void runOperator("restart_agents")}
        >
          Restart agents
        </button>
        {fleetAccess?.configured ? (
          <>
            <button
              type="button"
              className={`${styles.opBtn} ${pendingFleet === "wake_firstmate" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() =>
                void runFleetOperator("wake_firstmate", pendingFleet === "wake_firstmate")
              }
            >
              {pendingFleet === "wake_firstmate" ? "Confirm" : "Wake FirstMate"}
            </button>
            <button
              type="button"
              className={`${styles.opBtn} ${pendingFleet === "start_development" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() =>
                void runFleetOperator(
                  "start_development",
                  pendingFleet === "start_development",
                )
              }
            >
              {pendingFleet === "start_development" ? "Confirm" : "Start dev"}
            </button>
            <button
              type="button"
              className={`${styles.opBtn} ${pendingFleet === "run_next_backlog" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() =>
                void runFleetOperator("run_next_backlog", pendingFleet === "run_next_backlog")
              }
            >
              {pendingFleet === "run_next_backlog" ? "Confirm" : "Next backlog"}
            </button>
            <button
              type="button"
              className={`${styles.opBtn} ${styles.opBtnDanger} ${pendingFleet === "fleet_stop" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() => void runFleetOperator("fleet_stop", pendingFleet === "fleet_stop")}
            >
              {pendingFleet === "fleet_stop" ? "Confirm" : "Stop fleet"}
            </button>
          </>
        ) : null}
      </div>

      <div className={styles.speakRow}>
        <input
          className={styles.speakInput}
          type="text"
          placeholder="Type a command (works without mic)"
          value={typedLine}
          onChange={(e) => setTypedLine(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitTypedLine();
          }}
          aria-label="Type voice command"
        />
        <button className={styles.speakSend} type="button" onClick={submitTypedLine} disabled={!typedLine.trim()}>
          Send
        </button>
      </div>

      {agents.length > 0 ? (
        <div className={styles.agentRow} aria-label="Specialist agents">
          {agents.map((a) => {
            const freshness = a.cached ? formatFreshness(a.last_run, a.frame_id) : null;
            return (
              <span
                key={a.id}
                className={`${styles.agentChip} ${a.cached ? styles.ready : ""}`}
                title={
                  a.cached
                    ? freshness
                      ? `Cache warm, ${freshness}`
                      : "Cache warm"
                    : "Waiting for first tick"
                }
              >
                <span className={`${styles.agentDot} ${a.cached ? styles.ready : ""}`} aria-hidden />
                {a.name}
                {freshness ? (
                  <span className={`${styles.freshnessBadge} ${a.cached ? styles.ready : ""}`}>
                    {freshness}
                  </span>
                ) : null}
              </span>
            );
          })}
          <span className={styles.meta}>
            {agentsReady}/{agents.length} ready
          </span>
        </div>
      ) : null}

      <div className={styles.actions}>
        {voiceConnected ? (
          <button className={styles.secondary} onClick={disconnect} type="button">
            Disconnect
          </button>
        ) : (
          <button
            className={styles.primary}
            onClick={connect}
            disabled={state === "connecting"}
            type="button"
          >
            {state === "connecting" ? "Connecting..." : "Connect voice"}
          </button>
        )}
      </div>

      <div className={styles.frames}>
        {frames.map((frame) => {
          const isPending = pendingConfirm === frame.id;
          const isActive = activeFrame === frame.id;
          return (
            <button
              key={frame.id}
              type="button"
              className={`${styles.frameBtn} ${styles.frameBtnLive} ${isActive ? styles.frameBtnActive : ""}`}
              disabled={isActive}
              onClick={(ev) => onFrameClick(frame.id, ev)}
            >
              <span className={styles.frameLabel}>{frame.label}</span>
              <span className={styles.frameAgent}>{frame.agent_name}</span>
              {isPending ? (
                <span className={styles.frameConfirm} data-testid="frame-confirm-hint">
                  Confirm
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <p className={styles.hint}>
        Control layer: six specialists, FirstMate read-only, Hermes memory, Aether portfolio. Tap frames or use
        operator buttons. Shift+click fleet for a fresh read. Say first mate or github for access details.
      </p>
      <p className={styles.footer}>
        <a className={styles.footerLink} href="/voice-server">
          Server voice (no WebGPU)
        </a>
        {" · "}
        <a className={styles.footerLink} href="/voice-local">
          Client voice loop
        </a>
      </p>
    </section>
  );
}