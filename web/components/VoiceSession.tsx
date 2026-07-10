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
  INITIAL_UI_SESSION,
  reduceUiSession,
  uiStateLabel,
  type UiSessionContext,
  type UiSessionEvent,
} from "./voiceSessionState";

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

type ReviewQueueItem = {
  queue_id: number;
  title: string;
  status: string;
  brief_url?: string;
  created_at?: string;
};

type VoiceDiagnostics = {
  ok: boolean;
  checks?: {
    agents?: number;
    frame_run_ms?: number;
  };
};

type LatencyDiagnostics = {
  ok: boolean;
  sla_ok?: boolean;
  sla_target_ms?: number;
  timings_ms?: {
    frame_run_ms?: number | null;
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
  const [ui, dispatchUi] = useReducer(
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
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [voiceDiag, setVoiceDiag] = useState<VoiceDiagnostics | null>(null);
  const [latencyDiag, setLatencyDiag] = useState<LatencyDiagnostics | null>(null);
  const [micOn, setMicOn] = useState(false);
  const [typedLine, setTypedLine] = useState("");
  const [capabilities, setCapabilities] = useState<CapabilitiesPayload | null>(null);
  const [operatorBusy, setOperatorBusy] = useState(false);
  const [pendingFleet, setPendingFleet] = useState<FleetAction | null>(null);
  const [voiceSessionId] = useState(() => `pwa-${Date.now()}`);
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

  const loadReviewQueue = useCallback(() => {
    fetch(`${apiBase}/review-queue`)
      .then((r) => (r.ok ? r.json() : { pending: [] }))
      .then((data) => setReviewQueue((data.pending || []) as ReviewQueueItem[]))
      .catch(() => setReviewQueue([]));
  }, []);

  const loadDiagnostics = useCallback(() => {
    fetch(`${apiBase}/diagnostics/voice`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setVoiceDiag(data as VoiceDiagnostics | null))
      .catch(() => setVoiceDiag(null));

    fetch(`${apiBase}/diagnostics/latency`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setLatencyDiag(data as LatencyDiagnostics | null))
      .catch(() => setLatencyDiag(null));
  }, []);

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
    loadReviewQueue();
    loadDiagnostics();
    const agentsT = setInterval(() => {
      loadAgents();
      loadReviewQueue();
    }, 30000);
    const diagT = setInterval(loadDiagnostics, 60000);
    return () => {
      clearInterval(agentsT);
      clearInterval(diagT);
    };
  }, [loadAgents, loadDiagnostics, loadReviewQueue]);

  useEffect(() => {
    const onState = (s: ConnectionState) => {
      if (s === ConnectionState.Connected) {
        // Reducer preserves frame_running / confirm_pending when voice comes up mid-work.
        dispatchUi({ type: "CONNECT_OK" });
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
      }
    };

    const onMediaError = (error: Error) => {
      setMicOn(false);
      dispatchUi({ type: "ERROR" });
      setStatus(stripEmDash(`Microphone error: ${error.message}. Check browser permissions.`));
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
  }, [room]);

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
      dispatchUi({ type: "FRAME_START" });
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
          throw new Error(`Frame returned ${resp.status}`);
        }
        const data = await resp.json();

        if (data.status === "confirmation_required") {
          setPendingConfirm(frameId);
          dispatchUi({ type: "CONFIRMATION_REQUIRED" });
          const confirmSpoken = stripEmDash(data.spoken_summary as string);
          setStatus(
            voiceConnected
              ? confirmSpoken
              : `${confirmSpoken} Connect voice to hear TTS, then tap again to confirm.`,
          );
          await publishSpeak(confirmSpoken);
          return;
        }

        setPendingConfirm(null);
        dispatchUi({ type: "FRAME_OK" });
        const spoken = stripEmDash(data.spoken_summary as string);
        setStatus(
          voiceConnected ? spoken : `${spoken} Connect voice to hear TTS.`,
        );
        await publishSpeak(spoken);
        loadAgents();
        if (frameId === "queue_deep_review" && data.status === "ok") {
          const detail = data.detail as {
            brief_url?: string;
            title?: string;
            queue_id?: number;
          };
          if (detail?.brief_url) {
            setReviewQueue((prev) => {
              const id = detail.queue_id ?? prev.length;
              if (prev.some((r) => r.queue_id === id)) return prev;
              return [
                {
                  queue_id: id,
                  title: detail.title || "Deep review",
                  status: "pending",
                  brief_url: detail.brief_url,
                },
                ...prev,
              ];
            });
          }
          loadReviewQueue();
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Frame failed";
        dispatchUi({ type: "FRAME_FAIL_KEEP_VOICE" });
        setStatus(message);
      } finally {
        setActiveFrame(null);
      }
    },
    [apiBase, frames, loadAgents, loadReviewQueue, publishSpeak, voiceConnected],
  );

  const speakFromIntent = useCallback(
    async (transcript: string) => {
      const text = transcript.trim();
      if (!text) return;
      dispatchUi({ type: "FRAME_START" });
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
            const spoken = stripEmDash(opPreview.spoken);
            if (opPreview.action === "confirmation_required" && opPreview.pending_operator) {
              setPendingFleet(opPreview.pending_operator as FleetAction);
              dispatchUi({ type: "CONFIRMATION_REQUIRED" });
            } else {
              setPendingFleet(null);
              dispatchUi({ type: "FRAME_OK" });
            }
            if (opPreview.action === "run_all" || opPreview.action === "dispatch_squads") {
              void loadAgents();
            }
            const agentNote =
              opPreview.agents_used && opPreview.agents_used.length > 0
                ? ` (${opPreview.agents_used.length} agents)`
                : "";
            setStatus(spoken + agentNote);
            await publishSpeak(spoken);
            return;
          }
          const preview = data.preview?.spoken_summary as string | undefined;
          const frameId = data.frame_id as string | undefined;
          if (preview) {
            setStatus(stripEmDash(preview));
            await publishSpeak(preview);
            if (data.preview?.status === "confirmation_required" && frameId) {
              setPendingConfirm(frameId);
              dispatchUi({ type: "CONFIRMATION_REQUIRED" });
            } else {
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
          const spoken = stripEmDash(String(data.spoken || ""));
          if (data.action === "confirmation_required" && data.pending_operator) {
            setPendingFleet(data.pending_operator as FleetAction);
            dispatchUi({ type: "CONFIRMATION_REQUIRED" });
          } else {
            setPendingFleet(null);
            dispatchUi({ type: "FRAME_OK" });
          }
          if (data.action === "run_all" || data.action === "dispatch_squads") {
            void loadAgents();
          }
          const agentsUsed = data.agents_used as string[] | undefined;
          const agentNote =
            agentsUsed && agentsUsed.length > 0 ? ` (${agentsUsed.length} agents)` : "";
          setStatus(spoken + agentNote);
          await publishSpeak(spoken);
        } else {
          dispatchUi({ type: "FRAME_FAIL_KEEP_VOICE" });
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Request failed";
        dispatchUi({ type: "FRAME_FAIL_KEEP_VOICE" });
        setStatus(message);
      }
    },
    [loadAgents, publishSpeak, runFrame, voiceSessionId],
  );

  const runFleetOperator = useCallback(
    async (action: FleetAction, confirmed = false) => {
      if (operatorBusy) return;
      setOperatorBusy(true);
      dispatchUi({ type: "FRAME_START" });
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
          dispatchUi({ type: "CONFIRMATION_REQUIRED" });
          const spoken = stripEmDash(String(data.prompt || data.spoken || "Say yes to confirm."));
          setStatus(spoken);
          await publishSpeak(spoken);
          return;
        }
        setPendingFleet(null);
        dispatchUi({ type: "FRAME_OK" });
        const spoken = stripEmDash(String(data.spoken || `${label} completed.`));
        setStatus(spoken);
        await publishSpeak(spoken);
        loadAgents();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Fleet action failed";
        dispatchUi({ type: "FRAME_FAIL_KEEP_VOICE" });
        setStatus(message);
      } finally {
        setOperatorBusy(false);
      }
    },
    [apiBase, capabilities, loadAgents, operatorBusy, publishSpeak],
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
      try {
        if (kind === "capabilities") {
          await speakFromIntent("what can you do");
          return;
        }
        dispatchUi({ type: "FRAME_START" });
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
        dispatchUi({ type: "FRAME_OK" });
        loadAgents();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Operator action failed";
        dispatchUi({ type: "FRAME_FAIL_KEEP_VOICE" });
        setStatus(message);
      } finally {
        setOperatorBusy(false);
      }
    },
    [apiBase, loadAgents, operatorBusy, publishSpeak, speakFromIntent],
  );

  const connect = useCallback(async () => {
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
        if (status === 401 || status === 403 || status === 503) {
          throw new Error(
            stripEmDash(
              `Token failed (${status}). Check LiveKit API keys and that the advoi-voice container is running.`,
            ),
          );
        }
        throw new Error(`Token endpoint returned ${status}`);
      }
      const data = await resp.json();
      setRoomName(data.room_name || "");

      await room.connect(data.url, data.token);
      await room.startAudio();
      const micPub = await room.localParticipant.setMicrophoneEnabled(true);
      if (!micPub) {
        throw new Error("Microphone is blocked. Allow mic for this site and tap Connect again.");
      }
      setMicOn(true);
      room.remoteParticipants.forEach((participant) => {
        participant.audioTrackPublications.forEach((pub) => {
          if (pub.track) attachRemoteAudio(pub.track);
        });
      });
      dispatchUi({ type: "CONNECT_OK" });
      setStatus(
        `Joined ${data.room_name}. Mic on. Say fleet status, systems pulse, memory health, guardian status, or what can you do.`,
      );
    } catch (err) {
      let message = err instanceof Error ? err.message : "Connection failed";
      const tokenHint =
        message.startsWith("Token failed") || message.startsWith("Token endpoint returned");
      if (!tokenHint) {
        message = stripEmDash(
          `${message}. Check LiveKit WSS URL and allow microphone access.`,
        );
      }
      dispatchUi({ type: "CONNECT_FAIL" });
      setStatus(message);
    }
  }, [room]);

  const disconnect = useCallback(async () => {
    await room.localParticipant.setMicrophoneEnabled(false);
    await room.disconnect();
    dispatchUi({ type: "DISCONNECT" });
    setMicOn(false);
    setStatus("Session ended. Frames still work in text mode.");
    setPendingConfirm(null);
    setPendingFleet(null);
  }, [room]);

  const onFrameClick = (frameId: string, ev: React.MouseEvent) => {
    const refresh = ev.shiftKey || frameId === "fleet_status" && ev.detail === 2;
    if (pendingConfirm === frameId) {
      void runFrame(frameId, true, refresh);
      return;
    }
    void runFrame(frameId, false, refresh);
  };

  const agentsReady = agents.filter((a) => a.cached).length;
  const agentsTotal = agents.length || voiceDiag?.checks?.agents;
  const frameRunMs = latencyDiag?.timings_ms?.frame_run_ms;
  const expectedFrames = capabilities?.frame_count ?? 6;
  const deployStale = frames.length > 0 && frames.length < expectedFrames;
  const fleetAccess = capabilities?.systems_access?.firstmate_fleet;

  const stateLabel = uiStateLabel(state);

  return (
    <section className={styles.panel} data-ui-state={state}>
      <div className={styles.statusRow}>
        <span
          className={`${styles.stateChip} ${styles[state]}`}
          data-testid="ui-state-chip"
          data-state={state}
          title={`UI state: ${state}`}
        >
          <span className={`${styles.dot} ${styles[state]}`} aria-hidden />
          <span className={styles.stateChipLabel}>{stateLabel}</span>
        </span>
        <p className={styles.status} role="status" aria-live="polite">
          {status}
        </p>
      </div>
      {roomName ? <p className={styles.meta}>Room: {roomName}</p> : null}

      {voiceDiag || latencyDiag ? (
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
          {frameRunMs != null ? (
            <span className={styles.healthItem}>Frame: {frameRunMs}ms</span>
          ) : null}
          {latencyDiag?.sla_ok != null ? (
            <span
              className={`${styles.healthBadge} ${latencyDiag.sla_ok ? styles.healthOk : styles.healthWarn}`}
            >
              SLA {latencyDiag.sla_ok ? "ok" : "miss"}
              {latencyDiag.sla_target_ms != null ? ` (${latencyDiag.sla_target_ms}ms)` : ""}
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

      {state === "confirm_pending" ? (
        <p className={styles.confirmBanner} role="alert">
          Confirmation required — tap the pending control again or say yes.
        </p>
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
              {pendingFleet === "wake_firstmate" ? "Confirm wake" : "Wake FirstMate"}
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
              {pendingFleet === "start_development" ? "Confirm dev" : "Start dev"}
            </button>
            <button
              type="button"
              className={`${styles.opBtn} ${pendingFleet === "run_next_backlog" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() =>
                void runFleetOperator("run_next_backlog", pendingFleet === "run_next_backlog")
              }
            >
              {pendingFleet === "run_next_backlog" ? "Confirm backlog" : "Next backlog"}
            </button>
            <button
              type="button"
              className={`${styles.opBtn} ${styles.opBtnDanger} ${pendingFleet === "fleet_stop" ? styles.opBtnPending : ""}`}
              disabled={operatorBusy}
              onClick={() => void runFleetOperator("fleet_stop", pendingFleet === "fleet_stop")}
            >
              {pendingFleet === "fleet_stop" ? "Confirm stop" : "Stop fleet"}
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

      {reviewQueue.length > 0 ? (
        <div className={styles.reviewSection} aria-label="Pending deep reviews">
          <p className={styles.reviewHeading}>Review queue ({reviewQueue.length})</p>
          <ul className={styles.reviewList}>
            {reviewQueue.slice(0, 5).map((item) => (
              <li key={item.queue_id} className={styles.reviewItem}>
                <span className={styles.reviewTitle}>{item.title}</span>
                {item.brief_url ? (
                  <a
                    className={styles.reviewLink}
                    href={item.brief_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open brief
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

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
              {isPending ? <span className={styles.frameConfirm}>Tap again to confirm</span> : null}
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