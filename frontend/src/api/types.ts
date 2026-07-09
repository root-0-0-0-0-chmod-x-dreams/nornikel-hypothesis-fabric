import type { AgentStep, Document, Hypothesis, HypothesisSource, RoadmapStep } from "@/types";

export interface GenerateRequest {
  query: string;
  constraints?: {
    rawMaterials?: string[];
    budget?: string;
    equipment?: string[];
    regulations?: string[];
  };
  documentIds?: string[];
  maxHypotheses?: number;
  agentCycleDepth?: number;
  temperature?: number;
  language?: "ru" | "en" | "zh";
}

export interface GenerateResponse {
  query: string;
  hypotheses: Hypothesis[];
  contextDocuments?: Document[];
  retrievedParagraphs?: HypothesisSource[];
  generatedAt: string;
}

export interface StreamAgentStep {
  id: string;
  agent: AgentStep["agent"];
  title: string;
  summary: string;
  detail: string;
  timestamp: number;
  status: AgentStep["status"];
}

export interface StreamEvent {
  type: "progress" | "agent_step" | "hypothesis" | "hypothesis_passed" | "done" | "error";
  stage?: "analyzing" | "retrieving" | "generating" | "validating" | "report";
  elapsedSeconds?: number;
  step?: StreamAgentStep;
  current?: number;
  total?: number;
  message?: string;
  title?: string;
  index?: number;
  hypothesis?: Hypothesis;
  query?: string;
  hypotheses?: Hypothesis[];
  contextDocuments?: Document[];
  retrievedParagraphs?: HypothesisSource[];
  generatedAt?: string;
  totalPassed?: number;
}

export interface RoadmapRequest {
  availableEquipment?: string[];
  availableMaterials?: string[];
  timeConstraint?: string;
  budgetConstraint?: string;
}

export interface RoadmapResponse {
  hypothesisId: string;
  totalDuration: string;
  totalResources: string;
  steps: RoadmapStep[];
  sourceDetails?: import("@/types").HypothesisSource[];
}

export interface FeedbackRequest {
  status: "confirmed" | "refuted" | "partially_confirmed";
  notes?: string;
  actualResults?: string;
}

export interface FeedbackResponse {
  hypothesisId: string;
  status: string;
  recordedAt: string;
}

export interface HistoryItem {
  id: string;
  title: string;
  query: string;
  novelty: Hypothesis["novelty"];
  confidence: number;
  feedbackStatus: "confirmed" | "refuted" | "partially_confirmed" | null;
  createdAt: string;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}
