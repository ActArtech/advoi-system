"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./dashboard.module.css";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

type AgentRow = {
  id: string;
  name?: string;
  cached?: boolean;
  frame_id?: string;
  last_run?: { status?: string; timestamp?: number | string };
};

type SquadRow = {
  id: string;
  name: string;
  channel: string;
  agent_ids: string[];
  venture_id: string;
};

type PlatformDiag = {
  agents?: { ready?: number; total?: number; all_ready?: boolean };
  otel?: { enabled?: boolean; instrumented?: boolean };
  letta_enabled?: boolean;
  operational_bridge?: string;
  squads?: { total?: number };
};

type LatencyDiag = {
  timings_ms?: { run_six_ms?: number | null; frame_run_ms?: number | null };
  sla_ok?: boolean;
  sla_target_ms?: number;
};

export default function DashboardPage() {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [squads, setSquads] = useState<SquadRow[]>([]);
  const [platform, setPlatform] = useState<PlatformDiag | null>(null);
  const [latency, setLatency] = useState<LatencyDiag | null>(null);
  const [status, setStatus] = useState("Loading platform view...");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [agentRes, squadRes, platRes, latRes] = await Promise.all([
        fetch(`${apiBase}/agents`),
        fetch(`${apiBase}/squads`),
        fetch(`${apiBase}/diagnostics/platform`),
        fetch(`${apiBase}/diagnostics/latency`),
      ]);
      const agentData = await agentRes.json();
      const squadData = await squadRes.json();
      setAgents(agentData.agents || []);
      setSquads(squadData.squads || []);
      setPlatform(await platRes.json());
      setLatency(await latRes.json());
      setStatus("Ready. Run all 6 or dispatch squads to refresh agent cache.");
    } catch {
      setStatus("Could not load dashboard. Is the API running?");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runSix = useCallback(
    async (dispatchSquads: boolean) => {
      if (busy) return;
      setBusy(true);
      setStatus(dispatchSquads ? "Running 6 agents + dispatching squads..." : "Running all 6 agents...");
      try {
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
        const data = await resp.json();
        const squadNote =
          data.squads?.dispatched != null
            ? ` Squads: ${data.squads.dispatched}/${data.squads.total}.`
            : "";
        setStatus(String(data.spoken_summary || "Run complete.") + squadNote);
        await load();
      } catch (err) {
        setStatus(err instanceof Error ? err.message : "Run failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, load],
  );

  const agentsById = Object.fromEntries(agents.map((a) => [a.id, a]));
  const ready = platform?.agents?.ready ?? agents.filter((a) => a.cached).length;
  const total = platform?.agents?.total ?? agents.length;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>M6 · Portfolio dashboard</p>
        <h1>Agent graph</h1>
        <p className={styles.lede}>Six specialists, four squads, one parallel run.</p>
      </header>
      <p className={styles.nav}>
        <a href="/">Voice PWA</a>
      </p>

      <div className={styles.metrics} aria-label="Platform metrics">
        <span className={`${styles.metric} ${ready === total && total > 0 ? styles.metricOk : ""}`}>
          Agents {ready}/{total || 6} warm
        </span>
        {latency?.timings_ms?.run_six_ms != null ? (
          <span className={styles.metric}>Run-six {latency.timings_ms.run_six_ms}ms</span>
        ) : null}
        {latency?.sla_ok != null ? (
          <span className={`${styles.metric} ${latency.sla_ok ? styles.metricOk : styles.metricWarn}`}>
            SLA {latency.sla_ok ? "ok" : "miss"}
          </span>
        ) : null}
        <span className={styles.metric}>
          Memory {platform?.operational_bridge || "operational_store"}
        </span>
        <span className={styles.metric}>
          OTel {platform?.otel?.instrumented ? "on" : "off"}
        </span>
        <span className={styles.metric}>Squads {platform?.squads?.total ?? squads.length}</span>
      </div>

      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnPrimary}`}
          disabled={busy}
          onClick={() => void runSix(false)}
        >
          Run all 6
        </button>
        <button type="button" className={styles.btn} disabled={busy} onClick={() => void runSix(true)}>
          Run 6 + dispatch squads
        </button>
        <button type="button" className={styles.btn} disabled={busy} onClick={() => void load()}>
          Refresh
        </button>
      </div>

      <div className={styles.graph} aria-label="Squad agent graph">
        {squads.map((squad) => (
          <section key={squad.id} className={styles.squadBlock}>
            <h2 className={styles.squadTitle}>
              {squad.name} · {squad.channel} · {squad.venture_id}
            </h2>
            <div className={styles.agentGrid}>
              {squad.agent_ids.map((aid) => {
                const agent = agentsById[aid];
                const warm = agent?.cached;
                return (
                  <div
                    key={aid}
                    className={`${styles.agentCard} ${warm ? styles.agentCardWarm : ""}`}
                  >
                    <div className={styles.agentName}>{agent?.name || aid}</div>
                    <div className={styles.agentMeta}>
                      {agent?.frame_id || "—"}
                      <br />
                      {warm ? "warm" : "idle"}
                      {agent?.last_run?.status ? ` · ${agent.last_run.status}` : ""}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <p className={styles.statusLine}>{status}</p>
    </main>
  );
}