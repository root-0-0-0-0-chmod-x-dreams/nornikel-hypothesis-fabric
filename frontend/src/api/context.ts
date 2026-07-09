import type { ExtractedContent } from "@/types";

export function mapKbPreviewPayload(data: Record<string, unknown>): ExtractedContent {
  const meta = (data.metadata as Record<string, unknown>) || {};
  return {
    title: data.title != null ? String(data.title) : null,
    markdown: String(data.markdown ?? data.text ?? ""),
    text: String(data.text ?? data.markdown ?? ""),
    excerpt: data.excerpt != null ? String(data.excerpt) : null,
    html: String(data.html ?? ""),
    metadata: {
      title: meta.title != null ? String(meta.title) : null,
      description: meta.description != null ? String(meta.description) : null,
      author: null,
      siteName: meta.source != null ? String(meta.source) : null,
      language: null,
      canonicalUrl: null,
    },
    statusCode: null,
  };
}

export async function fetchKbDocumentContent(docId: string): Promise<ExtractedContent> {
  const res = await fetch(`/api/v1/context/documents/${encodeURIComponent(docId)}/content`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(String(err.detail || `Ошибка загрузки: ${res.status}`));
  }
  const data = await res.json();
  return mapKbPreviewPayload(data as Record<string, unknown>);
}
