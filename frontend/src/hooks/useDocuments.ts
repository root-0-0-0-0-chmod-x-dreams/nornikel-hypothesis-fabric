import { useState, useCallback, useEffect, useMemo } from "react";
import type { Document, ExtractedContent } from "@/types";
import { KNOWLEDGE_BASE_DOCUMENTS, isPinnedDocument, mapApiDocument } from "@/lib/knowledgeBase";
import { USE_MOCK_API } from "@/lib/hypothesis";

const STORAGE_KEY = "nornikel_user_documents";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

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
    origin: "user",
    pinned: false,
  } as Document;
}

function loadUserDocs(): Document[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const arr = JSON.parse(raw) as Record<string, unknown>[];
      return arr.map(deserializeDoc);
    }
  } catch {
    // ignore corrupted storage
  }
  return [];
}

function saveUserDocs(docs: Document[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(docs.map(serializeDoc)));
  } catch {
    // quota exceeded
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

async function fetchKbDocuments(): Promise<Document[]> {
  if (USE_MOCK_API) return KNOWLEDGE_BASE_DOCUMENTS;
  try {
    const res = await fetch("/api/v1/context/documents");
    if (!res.ok) return KNOWLEDGE_BASE_DOCUMENTS;
    const data = await res.json();
    const docs = (data.documents as Record<string, unknown>[]) ?? [];
    return docs.length ? docs.map(mapApiDocument) : KNOWLEDGE_BASE_DOCUMENTS;
  } catch {
    return KNOWLEDGE_BASE_DOCUMENTS;
  }
}

export function useDocuments() {
  const [userDocuments, setUserDocuments] = useState<Document[]>(() => loadUserDocs());
  const [knowledgeDocuments, setKnowledgeDocuments] = useState<Document[]>(KNOWLEDGE_BASE_DOCUMENTS);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    saveUserDocs(userDocuments);
  }, [userDocuments]);

  useEffect(() => {
    void fetchKbDocuments().then(setKnowledgeDocuments);
  }, []);

  const allContextDocuments = useMemo(
    () => [...knowledgeDocuments, ...userDocuments],
    [knowledgeDocuments, userDocuments],
  );

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
      origin: "user",
      pinned: false,
    };
    setUserDocuments((prev) => [doc, ...prev]);

    try {
      const content = await extractUrl(url);
      setUserDocuments((prev) =>
        prev.map((d) =>
          d.id === docId
            ? { ...d, status: "ready" as const, extractedContent: content, name: content.title || d.name }
            : d,
        ),
      );
    } catch (err) {
      setUserDocuments((prev) =>
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
      origin: "user",
      pinned: false,
    }));
    setUserDocuments((prev) => [...newDocs, ...prev]);
    setTimeout(() => {
      setUserDocuments((prev) =>
        prev.map((d) =>
          newDocs.some((nd) => nd.id === d.id) ? { ...d, status: "ready" as const } : d,
        ),
      );
      setUploading(false);
    }, 2000);
  }, []);

  const removeDocument = useCallback((id: string) => {
    setUserDocuments((prev) => {
      const doc = prev.find((d) => d.id === id);
      if (!doc || isPinnedDocument(doc)) return prev;
      if (doc.blobUrl) URL.revokeObjectURL(doc.blobUrl);
      return prev.filter((d) => d.id !== id);
    });
  }, []);

  return {
    knowledgeDocuments,
    userDocuments,
    documents: allContextDocuments,
    uploading,
    addByUrl,
    addByFiles,
    removeDocument,
  };
}
