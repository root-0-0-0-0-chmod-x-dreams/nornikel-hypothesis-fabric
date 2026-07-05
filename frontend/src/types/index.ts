export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  rationale: string;
  sources: string[];
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
  type: "pdf" | "docx" | "xlsx" | "url" | "image" | "other";
  size?: number;
  url: string;
  blobUrl?: string;
  extractedContent?: ExtractedContent;
  uploadedAt: Date;
  status: "uploading" | "processing" | "ready" | "error";
  errorMessage?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  attachments?: Document[];
  hypotheses?: Hypothesis[];
  timestamp: Date;
  isStreaming?: boolean;
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
}

export interface Roadmap {
  id: string;
  hypothesisId: string;
  steps: RoadmapStep[];
  totalDuration: string;
  totalResources: string;
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
