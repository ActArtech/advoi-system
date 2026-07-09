/** Detect browser storage issues before downloading ~200MB ONNX models. */

export type StorageProbeResult = {
  ok: boolean;
  reason?: "low_quota" | "idb_write_failed" | "probe_unavailable";
  quotaBytes?: number;
  usageBytes?: number;
  freeBytes?: number;
};

const MODEL_HEADROOM_BYTES = 280 * 1024 * 1024;

function isStorageFullMessage(message: string): boolean {
  return /NO_SPACE|quota|QuotaExceeded|FILE_ERROR|disk full|out of space/i.test(message);
}

export function isStorageFullError(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err);
  return isStorageFullMessage(msg);
}

export function formatModelLoadError(err: unknown): string {
  if (isStorageFullError(err)) {
    return (
      "Browser storage is full. Free disk space, clear site data for this site, " +
      "or use Server voice (/voice-server)."
    );
  }
  const msg = err instanceof Error ? err.message : String(err);
  if (/no available backend/i.test(msg)) {
    return (
      "On-device models could not start (usually low disk or blocked WASM). " +
      "Use Server voice (/voice-server) or clear Chrome site data."
    );
  }
  if (/webgpu/i.test(msg)) {
    return "WebGPU is unavailable here. WASM should still work if storage allows.";
  }
  return msg || "Model load failed";
}

async function probeIndexedDbWrite(): Promise<boolean> {
  if (typeof indexedDB === "undefined") return true;
  return new Promise((resolve) => {
    const name = `__advoi_storage_probe_${Date.now()}`;
    const req = indexedDB.open(name, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore("probe");
    };
    req.onsuccess = () => {
      const db = req.result;
      const tx = db.transaction("probe", "readwrite");
      const store = tx.objectStore("probe");
      store.put(new Uint8Array(64 * 1024), "chunk");
      tx.oncomplete = () => {
        db.close();
        indexedDB.deleteDatabase(name);
        resolve(true);
      };
      tx.onerror = () => {
        db.close();
        indexedDB.deleteDatabase(name);
        resolve(false);
      };
    };
    req.onerror = () => resolve(false);
  });
}

export async function probeBrowserStorage(): Promise<StorageProbeResult> {
  if (typeof navigator === "undefined") {
    return { ok: true, reason: "probe_unavailable" };
  }

  let quotaBytes: number | undefined;
  let usageBytes: number | undefined;
  let freeBytes: number | undefined;

  try {
    if (navigator.storage?.estimate) {
      const est = await navigator.storage.estimate();
      quotaBytes = est.quota;
      usageBytes = est.usage;
      if (quotaBytes != null && usageBytes != null) {
        freeBytes = quotaBytes - usageBytes;
        if (freeBytes < MODEL_HEADROOM_BYTES) {
          return { ok: false, reason: "low_quota", quotaBytes, usageBytes, freeBytes };
        }
      }
    }
  } catch {
    /* estimate optional */
  }

  const idbOk = await probeIndexedDbWrite();
  if (!idbOk) {
    return { ok: false, reason: "idb_write_failed", quotaBytes, usageBytes, freeBytes };
  }

  return { ok: true, quotaBytes, usageBytes, freeBytes };
}

export function storageProbeMessage(result: StorageProbeResult): string {
  if (result.ok) return "";
  if (result.reason === "low_quota" && result.freeBytes != null) {
    const freeMb = Math.max(0, Math.round(result.freeBytes / (1024 * 1024)));
    return `Low browser storage (${freeMb} MB free). Need ~280 MB for Kokoro/Parakeet. Using server voice instead.`;
  }
  return "Browser storage unavailable for model cache. Using server voice instead.";
}

const MODEL_CACHE_DB_NAMES = [
  "transformers-cache",
  "hf-transformers",
  "onnxruntime-web",
  "kokoro-js",
  "parakeet.js",
];

export async function clearModelCaches(): Promise<string[]> {
  const cleared: string[] = [];
  if (typeof indexedDB === "undefined") return cleared;

  await Promise.all(
    MODEL_CACHE_DB_NAMES.map(
      (name) =>
        new Promise<void>((resolve) => {
          const req = indexedDB.deleteDatabase(name);
          req.onsuccess = () => {
            cleared.push(name);
            resolve();
          };
          req.onerror = () => resolve();
          req.onblocked = () => resolve();
        }),
    ),
  );

  if (typeof caches !== "undefined") {
    try {
      const keys = await caches.keys();
      for (const key of keys) {
        if (/transform|onnx|kokoro|parakeet|huggingface/i.test(key)) {
          await caches.delete(key);
          cleared.push(`cache:${key}`);
        }
      }
    } catch {
      /* optional */
    }
  }

  return cleared;
}