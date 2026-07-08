import Link from "next/link";

type ReviewItem = {
  queue_id: number;
  title: string;
  source_frame: string;
  status: string;
  brief_url?: string;
  created_at?: string;
  metadata?: Record<string, unknown>;
};

async function loadBrief(id: string): Promise<ReviewItem | null> {
  const apiBase =
    process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") ||
    "https://advoi.keyteller.com/api";
  try {
    const resp = await fetch(`${apiBase}/review-queue/${id}`, {
      next: { revalidate: 30 },
    });
    if (!resp.ok) return null;
    const data = (await resp.json()) as { item?: ReviewItem };
    return data.item ?? null;
  } catch {
    return null;
  }
}

export default async function BriefPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await loadBrief(id);

  if (!item) {
    return (
      <main style={{ padding: "2rem", maxWidth: "40rem", margin: "0 auto" }}>
        <h1>Deep review brief</h1>
        <p>Brief #{id} was not found or the API is unavailable.</p>
        <p>
          <Link href="/">Back to ADVoi</Link>
        </p>
      </main>
    );
  }

  return (
    <main style={{ padding: "2rem", maxWidth: "40rem", margin: "0 auto" }}>
      <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>ADVoi deep review</p>
      <h1>{item.title}</h1>
      <p>
        <strong>Status:</strong> {item.status}
      </p>
      <p>
        <strong>Source frame:</strong> {item.source_frame}
      </p>
      {item.created_at ? (
        <p>
          <strong>Queued:</strong> {item.created_at}
        </p>
      ) : null}
      <p style={{ marginTop: "1.5rem", lineHeight: 1.6 }}>
        This brief was queued from voice or the PWA review frame. Open the main app to continue
        the conversation or run another frame.
      </p>
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/">Back to ADVoi PWA</Link>
      </p>
    </main>
  );
}