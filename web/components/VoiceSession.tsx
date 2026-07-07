"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  createLocalAudioTrack,
} from "livekit-client";
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

const tokenEndpoint =
  process.env.NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT || "/api/livekit/token";
const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

function attachRemoteAudio(track: { kind: Track.Kind; attach: () => HTMLMediaElement }) {
  if (track.kind !== Track.Kind.Audio) return;
  const el = track.attach();
  el.autoplay = true;
  document.body.appendChild(el);
}

export function VoiceSession() {
  const [state, setState] = useState<SessionState>("idle");
  const [status, setStatus] = useState("Tap connect to start a voice session.");
  const [roomName, setRoomName] = useState("");
  const [frames, setFrames] = useState<DecisionFrame[]>([]);
  const [activeFrame, setActiveFrame] = useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<string | null>(null);
  const room = useMemo(() => new Room({ adaptiveStream: true, dynacast: true }), []);

  useEffect(() => {
    fetch(`${apiBase}/frames`)
      .then((r) => r.json())
      .then((data) => setFrames(data.frames || []))
      .catch(() => {
        setFrames([]);
      });
  }, []);

  useEffect(() => {
    const onState = (s: ConnectionState) => {
      if (s === ConnectionState.Connected) {
        setState("connected");
        setStatus("Connected — speak or tap a decision frame.");
      } else if (s === ConnectionState.Connecting) {
        setState("connecting");
        setStatus("Connecting to LiveKit…");
      } else if (s === ConnectionState.Disconnected) {
        setState("idle");
        setStatus("Disconnected.");
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
      const payload = new TextEncoder().encode(JSON.stringify({ type: "speak", text }));
      await room.localParticipant.publishData(payload, { reliable: true });
    },
    [room],
  );

  const runFrame = useCallback(
    async (frameId: string, confirmed = false) => {
      if (state !== "connected") return;
      setActiveFrame(frameId);
      const frame = frames.find((f) => f.id === frameId);
      setStatus(`${frame?.agent_name || "Agent"} working…`);

      try {
        const resp = await fetch(`${apiBase}/frames/${frameId}/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmed }),
        });
        if (!resp.ok) {
          throw new Error(`Frame returned ${resp.status}`);
        }
        const data = await resp.json();

        if (data.status === "confirmation_required") {
          setPendingConfirm(frameId);
          setStatus(data.spoken_summary);
          await publishSpeak(data.spoken_summary);
          return;
        }

        setPendingConfirm(null);
        setStatus(data.spoken_summary);
        await publishSpeak(data.spoken_summary);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Frame failed";
        setState("error");
        setStatus(message);
      } finally {
        setActiveFrame(null);
      }
    },
    [apiBase, frames, publishSpeak, state],
  );

  const connect = useCallback(async () => {
    setState("connecting");
    setStatus("Requesting token…");
    try {
      const resp = await fetch(tokenEndpoint, { method: "POST" });
      if (!resp.ok) {
        throw new Error(`Token endpoint returned ${resp.status}`);
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
      const message = err instanceof Error ? err.message : "Connection failed";
      setState("error");
      setStatus(message);
    }
  }, [room]);

  const disconnect = useCallback(async () => {
    await room.disconnect();
    setState("idle");
    setStatus("Session ended.");
    setPendingConfirm(null);
  }, [room]);

  const onFrameClick = (frameId: string) => {
    if (pendingConfirm === frameId) {
      void runFrame(frameId, true);
      return;
    }
    void runFrame(frameId, false);
  };

  return (
    <section className={styles.panel}>
      <div className={styles.statusRow}>
        <span className={`${styles.dot} ${styles[state]}`} aria-hidden />
        <p className={styles.status}>{status}</p>
      </div>
      {roomName ? <p className={styles.meta}>Room: {roomName}</p> : null}

      <div className={styles.actions}>
        {state === "connected" ? (
          <button className={styles.secondary} onClick={disconnect} type="button">
            Disconnect
          </button>
        ) : (
          <button className={styles.primary} onClick={connect} disabled={state === "connecting"} type="button">
            {state === "connecting" ? "Connecting…" : "Connect voice"}
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
              className={`${styles.frameBtn} ${state === "connected" ? styles.frameBtnLive : ""} ${isActive ? styles.frameBtnActive : ""}`}
              disabled={state !== "connected" || isActive}
              onClick={() => onFrameClick(frame.id)}
            >
              <span className={styles.frameLabel}>{frame.label}</span>
              <span className={styles.frameAgent}>{frame.agent_name}</span>
              {isPending ? <span className={styles.frameConfirm}>Tap again to confirm</span> : null}
            </button>
          );
        })}
      </div>
      <p className={styles.hint}>
        Three specialist agents: fleet scout, brief curator, review queue. Connect voice first, then tap a frame or ask aloud.
      </p>
    </section>
  );
}