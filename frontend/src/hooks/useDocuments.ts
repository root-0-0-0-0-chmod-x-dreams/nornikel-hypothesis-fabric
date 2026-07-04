import { useState, useCallback } from "react";
import type { Document, ExtractedContent } from "@/types";

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

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>(DEMO_DOCS);
  const [uploading, setUploading] = useState(false);

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

  const addByFiles = useCallback((files: File[]) => {
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
    setTimeout(() => {
      setDocuments((prev) =>
        prev.map((d) =>
          newDocs.some((nd) => nd.id === d.id) ? { ...d, status: "ready" as const } : d,
        ),
      );
      setUploading(false);
    }, 2000);
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
