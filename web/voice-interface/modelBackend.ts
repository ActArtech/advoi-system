/** Pick ONNX runtime backend; Windows WebGPU is flaky for ORT (crbug.com/369219127). */

export type ModelBackend = "webgpu" | "wasm";

export function isWindows(): boolean {
  if (typeof navigator === "undefined") return false;
  return /Windows/i.test(navigator.userAgent);
}

/** Prefer WASM on Windows; WebGPU elsewhere when available. */
export function preferredModelBackend(): ModelBackend {
  if (typeof navigator === "undefined") return "wasm";
  if (isWindows()) return "wasm";
  if ("gpu" in navigator) return "webgpu";
  return "wasm";
}

export function backendLabel(backend: ModelBackend): string {
  return backend === "webgpu" ? "WebGPU" : "WASM";
}

export async function withBackendFallback<T>(
  run: (backend: ModelBackend) => Promise<T>,
): Promise<{ value: T; backend: ModelBackend }> {
  const preferred = preferredModelBackend();
  try {
    const value = await run(preferred);
    return { value, backend: preferred };
  } catch (first) {
    const fallback: ModelBackend = preferred === "webgpu" ? "wasm" : "webgpu";
    if (fallback === preferred) throw first;
    try {
      const value = await run(fallback);
      return { value, backend: fallback };
    } catch {
      throw first;
    }
  }
}