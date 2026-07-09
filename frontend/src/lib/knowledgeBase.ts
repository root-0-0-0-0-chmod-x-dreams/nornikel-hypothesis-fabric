import type { Document, HypothesisSource } from "@/types";

/** Pinned documents indexed in GraphRAG + Qdrant (cannot be removed from context). */
export const KNOWLEDGE_BASE_DOCUMENTS: Document[] = [
  {
    id: "kb-lossform-kgmk",
    name: "LossForm КГМК — анализ потерь Ni/Cu в хвостах",
    type: "xlsx",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 4,
    description: "Excel LossForm: статьи потерь по минералам и фракциям. Узлы графа + Qdrant.",
  },
  {
    id: "kb-book-lodeyshchikov",
    name: "Лодейщиков — Технология извлечения золота и серебра",
    type: "pdf",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 926,
    description: "Учебник обогащения, ~926 параграфов в Qdrant.",
  },
  {
    id: "kb-book-flotation",
    name: "Флотационные методы обогащения",
    type: "pdf",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 1200,
    description: "Справочник по флотации сульфидных руд.",
  },
  {
    id: "kb-book-metallurgy",
    name: "Металлургия благородных металлов",
    type: "pdf",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 890,
    description: "Процессы извлечения и обогащения.",
  },
  {
    id: "kb-book-tehnologiya",
    name: "Технология обогащения полезных ископаемых",
    type: "pdf",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 1100,
    description: "Классический учебник по обогащению.",
  },
  {
    id: "kb-schemes-flotation",
    name: "Схемы флотации ТОФ (VLM-транскрипты)",
    type: "other",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 12,
    description: "Технологические схемы: узлы графа equip_*, process_*.",
  },
  {
    id: "kb-regulations",
    name: "Регламенты и типовое оборудование",
    type: "docx",
    url: "",
    uploadedAt: new Date("2025-01-01"),
    status: "ready",
    pinned: true,
    origin: "knowledge_base",
    chunkCount: 4,
    description: "Ограничения CAPEX, списки оборудования.",
  },
];

/** Demo paragraphs with real chunk_id from GraphRAG case data. */
export const DEMO_RETRIEVED_PARAGRAPHS: HypothesisSource[] = [
  {
    title: "excel_lossform_кгмк_+71_closed_pnt_cp_ni, лист LossForm",
    type: "excel",
    chunkId: "excel_lossform_кгмк_+71_closed_pnt_cp_ni",
    url: "/api/v1/sources/chunks/excel_lossform_кгмк_+71_closed_pnt_cp_ni",
    excerpt: "Примесь в пирротине — 81.1 т Ni. Силикатная форма/валлериит — 256.7 т Ni.",
  },
  {
    title: "geokniga_lodeyshchikovvvtehnologiyaizvlecheniyazolotaiserebraizupornyh1.pdf, стр. 447, §903",
    type: "book",
    chunkId: "book_geokniga_lodeyshchikovvvtehnologiyaizvlecheniyazolotaiserebraizupornyh1_paragraph_p447_i902",
    url: "/api/v1/sources/chunks/book_geokniga_lodeyshchikovvvtehnologiyaizvlecheniyazolotaiserebraizupornyh1_paragraph_p447_i902",
    page: 447,
    paragraphIndex: 902,
    excerpt: "Магнитная сепарация сульфидов в слабом поле для выделения пирротиновых фракций…",
  },
  {
    title: "geokniga_flotacionnye_metody_obogashcheniya_0.pdf, стр. 312, §45",
    type: "book",
    chunkId: "book_geokniga_flotacionnye_metody_obogashcheniya_0_paragraph_p312_i45",
    url: "/api/v1/sources/chunks/book_geokniga_flotacionnye_metody_obogashcheniya_0_paragraph_p312_i45",
    page: 312,
    paragraphIndex: 45,
    excerpt: "Режим гидроциклонной классификации: влияние диаметра apex на плотность песков…",
  },
  {
    title: "Схема флотации.png",
    type: "scheme",
    chunkId: "scheme_схема_флотации",
    url: "/api/v1/sources/chunks/scheme_схема_флотации",
    excerpt: "Цикл: измельчение → классификация → флотация → доизмельчение. Узлы equip_fpm, process_flotation.",
  },
  {
    title: "geokniga_tehnologiyaobogashcheniyapoleznyhiskopaemyh.pdf, стр. 189, §12",
    type: "book",
    chunkId: "book_geokniga_tehnologiyaobogashcheniyapoleznyhiskopaemyh_paragraph_p189_i12",
    url: "/api/v1/sources/chunks/book_geokniga_tehnologiyaobogashcheniyapoleznyhiskopaemyh_paragraph_p189_i12",
    page: 189,
    paragraphIndex: 12,
    excerpt: "Изменение профиля футеровки мельницы для повышения доли ударного измельчения…",
  },
];

export function isPinnedDocument(doc: Document): boolean {
  return doc.pinned === true || doc.origin === "knowledge_base";
}

export function canPreviewDocument(doc: Document): boolean {
  return Boolean(doc.blobUrl || doc.previewAvailable || doc.extractedContent);
}

export function defaultPreviewMode(doc: Document): "info" | "file" | "content" {
  if (doc.previewAvailable && doc.origin === "knowledge_base") return "content";
  if (doc.extractedContent) return "content";
  if (doc.blobUrl && (doc.type === "pdf" || doc.type === "image")) return "file";
  return "info";
}

export function mapApiDocument(raw: Record<string, unknown>): Document {
  const fileUrl = raw.url ? String(raw.url) : "";
  return {
    id: String(raw.id),
    name: String(raw.name),
    type: (raw.type as Document["type"]) || "other",
    url: fileUrl.startsWith("/") ? fileUrl : fileUrl,
    uploadedAt: new Date(String(raw.uploadedAt ?? "2025-01-01")),
    status: (raw.status as Document["status"]) || "ready",
    pinned: Boolean(raw.pinned),
    origin: (raw.origin as Document["origin"]) || "knowledge_base",
    chunkCount: raw.chunkCount != null ? Number(raw.chunkCount) : undefined,
    description: raw.description ? String(raw.description) : undefined,
    previewAvailable: Boolean(raw.previewAvailable),
    previewKind: raw.previewKind as Document["previewKind"],
    indexedInGraphRag: raw.indexedInGraphRag != null ? Boolean(raw.indexedInGraphRag) : true,
  };
}
