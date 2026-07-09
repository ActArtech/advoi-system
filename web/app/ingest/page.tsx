"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./ingest.module.css";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

type IngestRow = {
  id: string;
  filename: string;
  status: string;
  project_slug?: string;
  venture_id?: string;
  priority?: string;
  dev_recommended?: boolean;
  summary?: string;
  route_confidence?: number;
};

export default function IngestPage() {
  const [items, setItems] = useState<IngestRow[]>([]);
  const [status, setStatus] = useState("Upload a file to route it to a project.");
  const [busy, setBusy] = useState(false);
  const [projectHint, setProjectHint] = useState("clapart");
  const [autoDispatch, setAutoDispatch] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/ingestion/items`);
      const data = await res.json();
      setItems(data.items || []);
    } catch {
      setStatus("Could not load ingestion queue.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onUpload = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (busy) return;
      const form = e.currentTarget;
      const input = form.elements.namedItem("file") as HTMLInputElement;
      if (!input.files?.length) {
        setStatus("Choose a file first.");
        return;
      }
      setBusy(true);
      setStatus("Uploading and routing...");
      try {
        const body = new FormData();
        body.append("file", input.files[0]);
        if (projectHint.trim()) body.append("project_hint", projectHint.trim());
        if (autoDispatch) {
          body.append("dispatch_dev", "true");
          body.append("confirmed", "true");
        }
        const res = await fetch(`${apiBase}/ingestion/upload`, { method: "POST", body });
        const data = await res.json();
        if (!data.ok) {
          setStatus(data.error || "Upload failed.");
        } else {
          const item = data.item as IngestRow;
          setStatus(
            `Routed to ${item.project_slug || "unknown"} (${item.priority} priority).` +
              (data.dispatch?.ok ? " Dev dispatched to FirstMate." : ""),
          );
          input.value = "";
          await load();
        }
      } catch {
        setStatus("Upload failed.");
      } finally {
        setBusy(false);
      }
    },
    [autoDispatch, busy, load, projectHint],
  );

  const dispatchDev = useCallback(
    async (id: string) => {
      if (busy) return;
      setBusy(true);
      setStatus("Dispatching to FirstMate...");
      try {
        const res = await fetch(`${apiBase}/ingestion/items/${id}/dispatch-dev`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmed: true, mode: "work" }),
        });
        const data = await res.json();
        setStatus(data.spoken || (data.ok ? "Dispatched." : data.status || "Dispatch failed."));
        await load();
      } catch {
        setStatus("Dispatch failed.");
      } finally {
        setBusy(false);
      }
    },
    [busy, load],
  );

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Ingestion</p>
        <h1>Upload and route</h1>
        <p className={styles.lede}>
          Upload text or markdown. ADVoi routes to a project and can dispatch dev work to FirstMate.
        </p>
        <p className={styles.nav}>
          <a href="/">Voice PWA</a> · <a href="/dashboard">Dashboard</a>
        </p>
      </header>

      <form className={styles.form} onSubmit={onUpload}>
        <label className={styles.label}>
          Project hint (optional)
          <input
            value={projectHint}
            onChange={(ev) => setProjectHint(ev.target.value)}
            placeholder="clapart"
          />
        </label>
        <label className={styles.label}>
          File (.txt, .md, .json, .csv)
          <input name="file" type="file" accept=".txt,.md,.markdown,.json,.csv,.log,.yaml,.yml" />
        </label>
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={autoDispatch}
            onChange={(ev) => setAutoDispatch(ev.target.checked)}
          />
          Dispatch to FirstMate after upload (when dev recommended)
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Working..." : "Upload and route"}
        </button>
      </form>

      <p className={styles.status}>{status}</p>

      <section className={styles.list}>
        <h2>Queue</h2>
        {items.length === 0 ? (
          <p className={styles.empty}>No items yet.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={item.id} className={styles.card}>
                <div className={styles.cardHead}>
                  <strong>{item.filename}</strong>
                  <span className={styles.badge}>{item.status}</span>
                </div>
                <p className={styles.meta}>
                  {item.project_slug || "unrouted"} · {item.priority} · conf{" "}
                  {item.route_confidence ?? 0}
                  {item.dev_recommended ? " · dev" : ""}
                </p>
                {item.summary ? <p className={styles.summary}>{item.summary}</p> : null}
                {item.status === "routed" && item.dev_recommended ? (
                  <button type="button" disabled={busy} onClick={() => void dispatchDev(item.id)}>
                    Start dev on FirstMate
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}