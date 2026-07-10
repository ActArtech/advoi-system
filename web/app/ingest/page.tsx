"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type IngestStatus,
  type LifecycleAction,
  type LifecycleActionId,
  actionUrl,
  actionsForStatus,
  lifecycleSuccessMessage,
  parseApiError,
  statusBadgeTone,
} from "../../components/ingestLifecycle";
import styles from "./ingest.module.css";

const apiBase = process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api";

type IngestRow = {
  id: string;
  filename: string;
  status: IngestStatus;
  project_slug?: string;
  venture_id?: string;
  priority?: string;
  dev_recommended?: boolean;
  summary?: string;
  route_confidence?: number;
  error?: string | null;
};

export default function IngestPage() {
  const [items, setItems] = useState<IngestRow[]>([]);
  const [status, setStatus] = useState(
    "Upload a file, then triage → needs review → approve → dispatch.",
  );
  const [statusIsError, setStatusIsError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [projectHint, setProjectHint] = useState("clapart");
  const [ventureHint, setVentureHint] = useState("");

  const setBanner = useCallback((message: string, isError = false) => {
    setStatus(message);
    setStatusIsError(isError);
  }, []);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/ingestion/items`);
      const data = await res.json();
      setItems(data.items || []);
    } catch {
      setBanner("Could not load ingestion queue.", true);
    }
  }, [setBanner]);

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
        setBanner("Choose a file first.", true);
        return;
      }
      setBusy(true);
      setBanner("Uploading…");
      try {
        const body = new FormData();
        body.append("file", input.files[0]);
        if (projectHint.trim()) body.append("project_hint", projectHint.trim());
        if (ventureHint.trim()) body.append("venture_hint", ventureHint.trim());
        // No dispatch_dev / confirmed — lifecycle requires explicit approve first.
        const res = await fetch(`${apiBase}/ingestion/upload`, { method: "POST", body });
        let data: unknown = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }

        if (res.status === 422 || !res.ok) {
          const err = parseApiError(res.status, data);
          setBanner(err.message, true);
          await load();
          return;
        }

        const payload = data as {
          ok?: boolean;
          error?: string;
          item?: IngestRow;
        };
        if (!payload.ok || payload.item?.status === "failed") {
          const err = parseApiError(res.status, data);
          setBanner(err.message || payload.error || "Upload failed.", true);
          await load();
          return;
        }

        const item = payload.item as IngestRow;
        setBanner(
          `Uploaded ${item.filename} (status: uploaded). Route: ${
            item.project_slug || "unrouted"
          } · ${item.priority || "medium"} priority. Next: Triage.`,
        );
        input.value = "";
        await load();
      } catch {
        setBanner("Upload failed.", true);
      } finally {
        setBusy(false);
      }
    },
    [busy, load, projectHint, setBanner, ventureHint],
  );

  const runAction = useCallback(
    async (item: IngestRow, action: LifecycleAction) => {
      if (busy) return;
      setBusy(true);
      setBusyId(item.id);
      setBanner(`${action.label}…`);
      try {
        const url = actionUrl(apiBase, item.id, action);
        const init: RequestInit = { method: action.method };
        if (action.body) {
          init.headers = { "Content-Type": "application/json" };
          init.body = JSON.stringify(action.body);
        }
        const res = await fetch(url, init);
        let data: unknown = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }

        if (!res.ok) {
          const err = parseApiError(res.status, data);
          setBanner(err.message, true);
          await load();
          return;
        }

        const payload = data as {
          ok?: boolean;
          spoken?: string;
          status?: string;
          item?: IngestRow;
          error?: string;
        };

        // dispatch-dev returns {ok, spoken, item?} — may be ok:false without HTTP error
        if (payload.ok === false) {
          const err = parseApiError(res.status, data);
          setBanner(err.message || payload.spoken || "Action failed.", true);
          await load();
          return;
        }

        const updated = payload.item;
        if (updated) {
          setBanner(
            lifecycleSuccessMessage(action.id as LifecycleActionId, updated) +
              (payload.spoken && action.id === "dispatch_dev" ? ` ${payload.spoken}` : ""),
          );
        } else {
          setBanner(
            payload.spoken ||
              lifecycleSuccessMessage(action.id as LifecycleActionId, {
                filename: item.filename,
                status: payload.status,
              }),
          );
        }
        await load();
      } catch {
        setBanner(`${action.label} failed.`, true);
      } finally {
        setBusy(false);
        setBusyId(null);
      }
    },
    [busy, load, setBanner],
  );

  return (
    <main className={styles.page} data-testid="ingest-page">
      <header className={styles.header}>
        <p className={styles.eyebrow}>Ingestion</p>
        <h1>Upload and route</h1>
        <p className={styles.lede}>
          Upload text or markdown. Advance each item through{" "}
          <strong>triage → needs review → approve → dispatch</strong> before FirstMate
          work is armed. Upload never auto-dispatches.
        </p>
        <p className={styles.nav}>
          <a href="/">Voice PWA</a> · <a href="/dashboard">Dashboard</a>
        </p>
      </header>

      <form className={styles.form} onSubmit={onUpload} data-testid="ingest-upload-form">
        <label className={styles.label}>
          Project hint (optional)
          <input
            value={projectHint}
            onChange={(ev) => setProjectHint(ev.target.value)}
            placeholder="clapart"
            data-testid="ingest-project-hint"
          />
        </label>
        <label className={styles.label}>
          Venture hint (optional — must be registered)
          <input
            value={ventureHint}
            onChange={(ev) => setVentureHint(ev.target.value)}
            placeholder="advoi-system"
            data-testid="ingest-venture-hint"
          />
        </label>
        <label className={styles.label}>
          File (.txt, .md, .json, .csv)
          <input
            name="file"
            type="file"
            accept=".txt,.md,.markdown,.json,.csv,.log,.yaml,.yml"
            data-testid="ingest-file"
          />
        </label>
        <button type="submit" disabled={busy} data-testid="ingest-upload-submit">
          {busy && !busyId ? "Working…" : "Upload"}
        </button>
      </form>

      <p
        className={statusIsError ? `${styles.status} ${styles.statusError}` : styles.status}
        data-testid="ingest-status"
        data-error={statusIsError ? "true" : "false"}
        role={statusIsError ? "alert" : "status"}
      >
        {status}
      </p>

      <section className={styles.list} data-testid="ingest-queue">
        <h2>Queue</h2>
        {items.length === 0 ? (
          <p className={styles.empty}>No items yet.</p>
        ) : (
          <ul>
            {items.map((item) => {
              const actions = actionsForStatus(item.status);
              const tone = statusBadgeTone(item.status);
              const itemBusy = busy && busyId === item.id;
              return (
                <li
                  key={item.id}
                  className={
                    item.status === "failed" ? `${styles.card} ${styles.cardFailed}` : styles.card
                  }
                  data-testid={`ingest-item-${item.id}`}
                  data-status={item.status}
                >
                  <div className={styles.cardHead}>
                    <strong>{item.filename}</strong>
                    <span
                      className={`${styles.badge} ${styles[`badge_${tone}`] || ""}`}
                      data-testid="ingest-item-status"
                      data-tone={tone}
                    >
                      {item.status}
                    </span>
                  </div>
                  <p className={styles.meta}>
                    {item.project_slug || "unrouted"}
                    {item.venture_id ? ` · ${item.venture_id}` : ""} · {item.priority || "medium"} ·
                    conf {item.route_confidence ?? 0}
                    {item.dev_recommended ? " · dev" : ""}
                  </p>
                  {item.summary ? <p className={styles.summary}>{item.summary}</p> : null}
                  {item.error || item.status === "failed" ? (
                    <p className={styles.itemError} data-testid="ingest-item-error" role="alert">
                      {item.error || "Item failed."}
                    </p>
                  ) : null}
                  {actions.length > 0 ? (
                    <div className={styles.actions} data-testid="ingest-item-actions">
                      {actions.map((action) => (
                        <button
                          key={action.id}
                          type="button"
                          disabled={busy}
                          data-testid={`ingest-action-${action.id}`}
                          data-action={action.id}
                          onClick={() => void runAction(item, action)}
                        >
                          {itemBusy ? "Working…" : action.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
