"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
} from "livekit-client";
import { stripEmDash } from "@/voice-interface/warmth";
import styles from "./VoiceSession.module.css";

type SessionState = "idle" | "connecting" | "connected" | "error";

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

const tokenEndpoint =
  process.env.NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT || "/api/livekit/token";
const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

const FRAME_SHORT: Record<string, string> = {
  fleet_status: "fleet",
  open_briefs: "briefs",
  queue_deep_review: "review",
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
  const [state, setState] = useState<SessionState>("idle");
  const [status, setStatus] = useState("Tap connect for voice, or tap a frame to test agents.");
  const [roomName, setRoomName] = useState("");
  const [frames, setFrames] = useState<DecisionFrame[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [activeFrame, setActiveFrame] = useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<string | null>(null);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [voiceDiag, setVoiceDiag] = useState<VoiceDiagnostics | null>(null);
  const [latencyDiag, setLatencyDiag] = useState<LatencyDiagnostics | null>(null);
  const room = useMemo(() => new Room({ adaptiveStream: true, dynacast: true }), []);

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
        setState("connected");
        setStatus("Connected. Speak or tap a decision frame.");
      } else if (s === ConnectionState.Connecting) {
        setState("connecting");
        setStatus("Connecting to LiveKit...");
      } else if (s === ConnectionState.Disconnected) {
        setState("idle");
        setStatus("Disconnected. Frames still work in text mode.");
        setPendingConfirm(null);
      }
    };

    room.on(RoomEvent.ConnectionStateChanged, onState);
    room.on(RoomEvent.TrackSubscribed, attachRemoteAudio);

    return () => {
      room.off(RoomEvent.ConnectionStateChanged, onState);
      room.disconnect();
    };
  }, [room]);

  const publishSpeak = useCallback(
    async (text: string) => {
      if (state !== "connected") return;
      await room.startAudio();
      const payload = new TextEncoder().encode(
        JSON.stringify({ type: "speak", text: stripEmDash(text) }),
      );
      await room.localParticipant.publishData(payload, { reliable: true });
    },
    [room, state],
  );

  const runFrame = useCallback(
    async (frameId: string, confirmed = false, refresh = false) => {
      setActiveFrame(frameId);
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
          const confirmSpoken = stripEmDash(data.spoken_summary as string);
          setStatus(
            state === "connected"
              ? confirmSpoken
              : `${confirmSpoken} Connect voice to hear TTS, then tap again to confirm.`,
          );
          await publishSpeak(confirmSpoken);
          return;
        }

        setPendingConfirm(null);
        const spoken = stripEmDash(data.spoken_summary as string);
        setStatus(
          state === "connected" ? spoken : `${spoken} Connect voice to hear TTS.`,
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
        setState((s) => (s === "connected" ? "connected" : "error"));
        setStatus(message);
      } finally {
        setActiveFrame(null);
      }
    },
    [apiBase, frames, loadAgents, loadReviewQueue, publishSpeak],
  );

  const connect = useCallback(async () => {
    setState("connecting");
    setStatus("Requesting token...");
    try {
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

      const mic = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
      });
      await room.connect(data.url, data.token);
      await room.startAudio();
      await room.localParticipant.publishTrack(mic);
      room.remoteParticipants.forEach((participant) => {
        participant.audioTrackPublications.forEach((pub) => {
          if (pub.track) attachRemoteAudio(pub.track);
        });
      });
      setStatus(`Joined ${data.room_name}. ADVoi should greet you.`);
    } catch (err) {
      let message = err instanceof Error ? err.message : "Connection failed";
      const tokenHint =
        message.startsWith("Token failed") || message.startsWith("Token endpoint returned");
      if (!tokenHint) {
        message = stripEmDash(
          `${message}. Check LiveKit WSS URL and allow microphone access.`,
        );
      }
      setState("error");
      setStatus(message);
    }
  }, [room]);

  const disconnect = useCallback(async () => {
    await room.disconnect();
    setState("idle");
    setStatus("Session ended. Frames still work in text mode.");
    setPendingConfirm(null);
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

  return (
    <section className={styles.panel}>
      <div className={styles.statusRow}>
        <span className={`${styles.dot} ${styles[state]}`} aria-hidden />
        <p className={styles.status}>{status}</p>
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

      {state === "connected" ? (
        <p className={styles.intentHint}>Try: fleet status, open briefs, queue review</p>
      ) : null}

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
        {state === "connected" ? (
          <button className={styles.secondary} onClick={disconnect} type="button">
            Disconnect
          </button>
        ) : (
          <button className={styles.primary} onClick={connect} disabled={state === "connecting"} type="button">
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
        Three specialist agents run in the background. Tap frames anytime (text mode). Connect voice for TTS.
        Shift+click fleet for a fresh read.
      </p>
      <p className={styles.footer}>
        <a className={styles.footerLink} href="/voice-local">
          Try client voice loop
        </a>
      </p>
    </section>
  );
}