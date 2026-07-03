export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  rationale: string;
  sources: string[];
  novelty: "high" | "medium" | "low";
  risks: { technical: string; economic: string };
  expectedValue: string;
  mechanism: string;
}

export interface Document {
  id: string;
  name: string;
  type: "pdf" | "docx" | "xlsx" | "url" | "image" | "other";
  size?: number;
  url: string;
  blobUrl?: string;
  uploadedAt: Date;
  status: "uploading" | "processing" | "ready" | "error";
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
