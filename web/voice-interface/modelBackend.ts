/** Pick ONNX runtime backend; WASM-first for reliability (WebGPU often blocked in Chrome). */

import { isStorageFullError } from "./storageProbe";

export type ModelBackend = "webgpu" | "wasm";

type WebGpuNavigator = Navigator & {
  gpu?: { requestAdapter: () => Promise<unknown> };
};

export function isWindows(): boolean {
  if (typeof navigator === "undefined") return false;
  return /Windows/i.test(navigator.userAgent);
}

let webGpuProbe: Promise<boolean> | null = null;

/** True only when requestAdapter succeeds (not just navigator.gpu present). */
export async function webGpuAdapterAvailable(): Promise<boolean> {
  if (typeof navigator === "undefined") return false;
  const nav = navigator as WebGpuNavigator;
  if (!nav.gpu) return false;
  if (!webGpuProbe) {
    webGpuProbe = (async () => {
      try {
        const adapter = await nav.gpu!.requestAdapter();
        return adapter != null;
      } catch {
        return false;
      }
    })();
  }
  return webGpuProbe;
}

/** Always WASM first — WebGPU requires flags/adapters many browsers lack. */
export function preferredModelBackend(): ModelBackend {
  return "wasm";
}

export function backendLabel(backend: ModelBackend): string {
  return backend === "webgpu" ? "WebGPU" : "WASM";
}

export async function withBackendFallback<T>(
  run: (backend: ModelBackend) => Promise<T>,
): Promise<{ value: T; backend: ModelBackend }> {
  try {
    const value = await run("wasm");
    return { value, backend: "wasm" };
  } catch (wasmErr) {
    if (!isStorageFullError(wasmErr) && (await webGpuAdapterAvailable())) {
      try {
        const value = await run("webgpu");
        return { value, backend: "webgpu" };
      } catch {
        /* fall through */
      }
    }
    throw wasmErr;
  }
}