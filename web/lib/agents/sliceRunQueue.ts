/**
 * FIFO run queue for agent slice batches.
 * Keeps Python mirror in tests/test_agent_slices.py in sync.
 */

export type SliceQueueItem = {
  id: string;
  label: string;
};

export type SliceQueueEntry = SliceQueueItem & {
  run: () => Promise<void>;
};

export const MAX_SLICE_QUEUE_DEPTH = 5;

export function createQueueEntry(label: string, run: () => Promise<void>): SliceQueueEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    label,
    run,
  };
}

/** Enqueue with cap; drops oldest when over max depth. */
export function enqueueSliceRun(
  queue: SliceQueueEntry[],
  entry: SliceQueueEntry,
  maxDepth = MAX_SLICE_QUEUE_DEPTH,
): SliceQueueEntry[] {
  const next = [...queue, entry];
  if (next.length <= maxDepth) return next;
  return next.slice(next.length - maxDepth);
}

export function dequeueSliceRun(queue: SliceQueueEntry[]): {
  queue: SliceQueueEntry[];
  next: SliceQueueEntry | null;
} {
  if (queue.length === 0) return { queue, next: null };
  const [next, ...rest] = queue;
  return { queue: rest, next };
}

export function queueLabels(queue: readonly SliceQueueEntry[]): string[] {
  return queue.map((q) => q.label);
}

export function queueItemSnapshots(queue: readonly SliceQueueEntry[]): SliceQueueItem[] {
  return queue.map(({ id, label }) => ({ id, label }));
}

export function removeQueueItem(queue: SliceQueueEntry[], id: string): SliceQueueEntry[] {
  return queue.filter((q) => q.id !== id);
}

/** Move item to front of queue (next to run after current batch). */
export function bumpQueueItem(queue: SliceQueueEntry[], id: string): SliceQueueEntry[] {
  const idx = queue.findIndex((q) => q.id === id);
  if (idx <= 0) return queue;
  const item = queue[idx];
  const rest = queue.filter((_, i) => i !== idx);
  return [item, ...rest];
}

/** Swap item one position up or down in the waiting queue. */
export function moveQueueItem(
  queue: SliceQueueEntry[],
  id: string,
  direction: "up" | "down",
): SliceQueueEntry[] {
  const idx = queue.findIndex((q) => q.id === id);
  if (idx < 0) return queue;
  const target = direction === "up" ? idx - 1 : idx + 1;
  if (target < 0 || target >= queue.length) return queue;
  const next = [...queue];
  [next[idx], next[target]] = [next[target], next[idx]];
  return next;
}