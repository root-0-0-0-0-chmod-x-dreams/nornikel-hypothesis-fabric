import { useState, useCallback, useEffect } from "react";
import type { Document, ExtractedContent } from "@/types";

const STORAGE_KEY = "nornikel_documents";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

const DEMO_DOCS: Document[] = [
  {
    id: "d1",
    name: "Патент RU 2 7XX XXX — Жаропрочный сплав на основе никеля.pdf",
    type: "pdf",
    size: 2_450_000,
    url: "",
    uploadedAt: new Date("2025-06-15"),
    status: "ready",
  },
  {
    id: "d2",
    name: "Smith et al. — Ni-based superalloy creep behavior (2023).pdf",
    type: "pdf",
    size: 4_200_000,
    url: "",
    uploadedAt: new Date("2025-06-20"),
    status: "ready",
  },
  {
    id: "d3",
    name: "Лабораторный журнал — плавки №45-52.xlsx",
    type: "xlsx",
    size: 1_800_000,
    url: "",
    uploadedAt: new Date("2025-06-28"),
    status: "ready",
  },
];

function serializeDoc(doc: Document): Record<string, unknown> {
  const { blobUrl: _, ...rest } = doc;
  return {
    ...rest,
    uploadedAt: doc.uploadedAt.toISOString(),
  };
}

function deserializeDoc(raw: Record<string, unknown>): Document {
  return {
    ...raw,
    uploadedAt: new Date(raw.uploadedAt as string),
    blobUrl: undefined,
    size: raw.size as number | undefined,
  } as Document;
}

function loadDocs(): Document[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const arr = JSON.parse(raw) as Record<string, unknown>[];
      if (arr.length > 0) return arr.map(deserializeDoc);
    }
  } catch {
    // corrupted data, fall through to demo
  }
  return DEMO_DOCS;
}

function saveDocs(docs: Document[]) {
  try {
    const serialized = docs.map(serializeDoc);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serialized));
  } catch {
    // quota exceeded or other error, silently fail
  }
}

async function extractUrl(url: string): Promise<ExtractedContent> {
  const res = await fetch("/api/v1/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Ошибка экстракции: ${res.status}`);
  }

  const data = await res.json();
  return {
    title: data.title ?? null,
    markdown: data.markdown,
    text: data.text,
    excerpt: data.excerpt ?? null,
    html: data.html,
    metadata: {
      title: data.metadata?.title ?? null,
      description: data.metadata?.description ?? null,
      author: data.metadata?.author ?? null,
      siteName: data.metadata?.site_name ?? null,
      language: data.metadata?.language ?? null,
      canonicalUrl: data.metadata?.canonical_url ?? null,
    },
    statusCode: data.status_code ?? null,
  };
}

async function convertFile(file: File): Promise<{ markdown: string; metadata: Record<string, unknown> }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/v1/convert", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Ошибка конвертации: ${res.status}`);
  }

  const data = await res.json();
  return {
    markdown: data.markdown_content || "",
    metadata: data.metadata || {},
  };
}

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>(() => loadDocs());
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    saveDocs(documents);
  }, [documents]);

  const addByUrl = useCallback(async (url: string) => {
    setUploading(true);
    const docId = generateId();
    const doc: Document = {
      id: docId,
      name: decodeURIComponent(new URL(url).pathname.split("/").pop() || url),
      type: "url",
      url,
      uploadedAt: new Date(),
      status: "processing",
    };
    setDocuments((prev) => [doc, ...prev]);

    try {
      const content = await extractUrl(url);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === docId
            ? { ...d, status: "ready" as const, extractedContent: content, name: content.title || d.name }
            : d,
        ),
      );
    } catch (err) {
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === docId
            ? {
                ...d,
                status: "error" as const,
                errorMessage: (err as Error).message || "Не удалось извлечь содержимое",
              }
            : d,
        ),
      );
    } finally {
      setUploading(false);
    }
  }, []);

  const addByFiles = useCallback(async (files: File[]) => {
    setUploading(true);
    const newDocs: Document[] = files.map((file) => ({
      id: generateId(),
      name: file.name,
      type: (file.name.split(".").pop()?.toLowerCase() as Document["type"]) || "other",
      size: file.size,
      url: "",
      blobUrl: URL.createObjectURL(file),
      uploadedAt: new Date(),
      status: "processing" as const,
    }));
    setDocuments((prev) => [...newDocs, ...prev]);

    for (const doc of newDocs) {
      const file = files.find((f) => f.name === doc.name && f.size === doc.size);
      if (!file) continue;
      try {
        const result = await convertFile(file);
        setDocuments((prev) =>
          prev.map((d) =>
            d.id === doc.id
              ? {
                  ...d,
                  status: "ready" as const,
                  extractedContent: {
                    title: doc.name,
                    markdown: result.markdown,
                    text: result.markdown,
                    excerpt: result.markdown.substring(0, 280),
                    html: "",
                    metadata: {
                      title: doc.name,
                      description: null,
                      author: null,
                      siteName: null,
                      language: null,
                      canonicalUrl: null,
                    },
                    statusCode: 200,
                  },
                }
              : d,
          ),
        );
      } catch (err) {
        setDocuments((prev) =>
          prev.map((d) =>
            d.id === doc.id
              ? {
                  ...d,
                  status: "error" as const,
                  errorMessage: (err as Error).message || "Не удалось конвертировать файл",
                }
              : d,
          ),
        );
      }
    }
    setUploading(false);
  }, []);

  const removeDocument = useCallback((id: string) => {
    setDocuments((prev) => {
      const doc = prev.find((d) => d.id === id);
      if (doc?.blobUrl) {
        URL.revokeObjectURL(doc.blobUrl);
      }
      return prev.filter((d) => d.id !== id);
    });
  }, []);

  return { documents, uploading, addByUrl, addByFiles, removeDocument };
}
