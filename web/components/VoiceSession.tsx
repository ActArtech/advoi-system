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

// Same-origin in production (Traefik routes /api → advoi-api). Override for non-proxy dev setups.
const tokenEndpoint =
  process.env.NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT || "/api/livekit/token";

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
  const room = useMemo(() => new Room({ adaptiveStream: true, dynacast: true }), []);

  useEffect(() => {
    const onState = (s: ConnectionState) => {
      if (s === ConnectionState.Connected) {
        setState("connected");
        setStatus("Connected — speak when ready.");
      } else if (s === ConnectionState.Connecting) {
        setState("connecting");
        setStatus("Connecting to LiveKit…");
      } else if (s === ConnectionState.Disconnected) {
        setState("idle");
        setStatus("Disconnected.");
      }
    };

    room.on(RoomEvent.ConnectionStateChanged, onState);
    room.on(RoomEvent.TrackSubscribed, attachRemoteAudio);

    return () => {
      room.off(RoomEvent.ConnectionStateChanged, onState);
      room.disconnect();
    };
  }, [room]);

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
  }, [room]);

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
        <button type="button" className={styles.frameBtn} disabled>
          Option A — Fleet status
        </button>
        <button type="button" className={styles.frameBtn} disabled>
          Option B — Open briefs
        </button>
        <button type="button" className={styles.frameBtn} disabled>
          Option C — Queue deep review
        </button>
      </div>
      <p className={styles.hint}>Decision frame buttons ship in Stage 2. Voice path is live in Stage 1.</p>
    </section>
  );
}