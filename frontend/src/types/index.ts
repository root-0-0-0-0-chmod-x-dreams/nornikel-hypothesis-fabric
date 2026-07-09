export interface HypothesisSource {
  title: string;
  url?: string;
  type?: string;
  excerpt?: string;
  chunkId?: string;
  page?: number;
  paragraphIndex?: number;
}

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  rationale: string;
  sources: string[];
  sourceDetails?: HypothesisSource[];
  novelty: "high" | "medium" | "low";
  noveltyRationale?: string;
  confidence?: number;
  risks: { technical: string; economic: string };
  expectedValue: string;
  mechanism: string;
}

export interface ExtractedContent {
  title: string | null;
  markdown: string;
  text: string;
  excerpt: string | null;
  html: string;
  metadata: {
    title: string | null;
    description: string | null;
    author: string | null;
    siteName: string | null;
    language: string | null;
    canonicalUrl: string | null;
  };
  statusCode: number | null;
}

export interface Document {
  id: string;
  name: string;
  type: "pdf" | "docx" | "xlsx" | "xls" | "csv" | "url" | "image" | "other";
  size?: number;
  url: string;
  blobUrl?: string;
  extractedContent?: ExtractedContent;
  uploadedAt: Date;
  status: "uploading" | "processing" | "ready" | "error";
  errorMessage?: string;
  /** Fixed in GraphRAG/Qdrant context — cannot be removed */
  pinned?: boolean;
  origin?: "user" | "knowledge_base";
  chunkCount?: number;
  description?: string;
  /** KB document can be previewed via /context/documents/{id}/content */
  previewAvailable?: boolean;
  previewKind?: "book" | "scheme" | "regulation" | "spreadsheet" | "document";
  indexedInGraphRag?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  attachments?: Document[];
  hypotheses?: Hypothesis[];
  agentSteps?: AgentStep[];
  timestamp: Date;
  isStreaming?: boolean;
  generationElapsed?: number;
}

export interface AgentStep {
  id: string;
  agent: "generator" | "actor" | "judge";
  title: string;
  summary: string;
  detail: string;
  timestamp: number;
  status: "pending" | "running" | "done";
}

export interface GenerationSettings {
  maxHypotheses: number;
  agentCycleDepth: number;
  temperature: number;
}

export interface RoadmapStep {
  id: string;
  order: number;
  title: string;
  description: string;
  resources: string;
  duration: string;
  successCriteria: string;
  failureCriteria: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  sourceDetails?: HypothesisSource[];
}

export interface Roadmap {
  id: string;
  hypothesisId: string;
  steps: RoadmapStep[];
  totalDuration: string;
  totalResources: string;
  sourceDetails?: HypothesisSource[];
}

export interface QueryContext {
  targetProperty: string;
  constraints: {
    rawMaterials: string[];
    budget: string;
    equipment: string[];
    regulations: string[];
  };
  documents: Document[];
}
