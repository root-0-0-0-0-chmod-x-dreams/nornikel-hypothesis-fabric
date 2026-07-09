import type { Hypothesis, HypothesisSource, Roadmap, RoadmapStep } from "@/types";
import type { RoadmapResponse } from "@/api/types";

const NOVELTY_LABEL: Record<Hypothesis["novelty"], string> = {
  high: "Высокая новизна",
  medium: "Средняя новизна",
  low: "Низкая новизна",
};

const IMPACT_LABEL = {
  high: "Высокое влияние",
  medium: "Среднее влияние",
  low: "Низкое влияние",
} as const;

export function noveltyLabel(novelty: Hypothesis["novelty"]): string {
  return NOVELTY_LABEL[novelty];
}

export function impactLevel(hypothesis: Hypothesis): keyof typeof IMPACT_LABEL {
  const confidence = hypothesis.confidence ?? 0.7;
  if (confidence >= 0.85) return "high";
  if (confidence >= 0.7) return "medium";
  return "low";
}

export function impactLabel(hypothesis: Hypothesis): string {
  return IMPACT_LABEL[impactLevel(hypothesis)];
}

export function parseSourceEntry(source: string): HypothesisSource {
  const urlMatch = source.match(/https?:\/\/[^\s,)]+/);
  return {
    title: source.replace(/https?:\/\/[^\s,)]+/g, "").replace(/[—–-]\s*$/, "").trim() || source,
    url: urlMatch?.[0],
  };
}

function mapKnowledgeSource(raw: Record<string, unknown>): HypothesisSource {
  const chunkId = raw.chunkId ?? raw.chunk_id;
  const citation = (raw.citation ?? {}) as Record<string, unknown>;
  const entry: HypothesisSource = {
    title: String(raw.title ?? citation.display_ref ?? chunkId ?? "Источник"),
    type: String(raw.type ?? "db"),
    excerpt: String(raw.excerpt ?? raw.relevance ?? ""),
  };
  if (chunkId) {
    entry.chunkId = String(chunkId);
    entry.url = String(raw.url ?? `/api/v1/sources/chunks/${chunkId}`);
  } else if (raw.url) {
    entry.url = String(raw.url);
  } else if (raw.source_url) {
    entry.url = String(raw.source_url);
  }
  const page = raw.page ?? citation.page;
  const paragraphIndex = raw.paragraphIndex ?? raw.paragraph_index ?? citation.paragraph_index;
  if (page != null) entry.page = Number(page);
  if (paragraphIndex != null) entry.paragraphIndex = Number(paragraphIndex);
  return entry;
}

export function normalizeSources(sources: string[] | undefined): HypothesisSource[] {
  return (sources ?? []).map(parseSourceEntry);
}

export function normalizeSourceDetails(
  details: unknown[] | undefined,
  fallbackSources?: string[],
): HypothesisSource[] {
  if (details?.length) {
    return details.map((d) => mapKnowledgeSource(d as Record<string, unknown>));
  }
  return normalizeSources(fallbackSources);
}

/** Map hypothesis-factory backend payload → frontend Hypothesis */
export function normalizeBackendHypothesis(raw: Record<string, unknown>, index?: number): Hypothesis {
  const actor = (raw.actor_validation ?? {}) as Record<string, unknown>;
  const judge = (raw.judge_evaluation ?? {}) as Record<string, unknown>;
  const actorSources = (actor.sources as Array<{ title?: string; type?: string; relevance?: string; chunk_id?: string }>) ?? [];
  const refs = (raw.references as string[]) ?? [];
  const knowledgeSources = (raw.knowledge_sources as Record<string, unknown>[]) ?? [];
  const apiSourceDetails = raw.sourceDetails as Record<string, unknown>[] | undefined;

  const sourceStrings = [
    ...refs,
    ...actorSources.map((s) => {
      const parts = [s.type, s.title, s.relevance].filter(Boolean);
      return parts.join(" — ");
    }),
    ...knowledgeSources.map((s) => String(s.title ?? "")),
  ].filter(Boolean);

  const actorRisks = (actor.risks ?? {}) as { technical?: string; economic?: string };
  const novelty = (raw.novelty as Hypothesis["novelty"]) || "medium";
  const finalScore = Number(judge.final_score ?? 0);
  const confidence = finalScore > 0 ? Math.min(1, finalScore / 5) : Number(raw.confidence ?? 0) || undefined;

  const sourceDetails = normalizeSourceDetails(
    apiSourceDetails ?? (knowledgeSources.length ? knowledgeSources : undefined),
    sourceStrings.length ? sourceStrings : ["GraphRAG / внутренние документы"],
  );

  return {
    id: String(raw.id ?? `h${(index ?? 0) + 1}`),
    title: String(raw.title ?? `Гипотеза ${(index ?? 0) + 1}`),
    description: String(raw.description ?? ""),
    rationale: String(raw.rationale ?? actor.justification ?? ""),
    mechanism: String(raw.mechanism ?? actor.mechanism_detail ?? ""),
    expectedValue: String(raw.expected_impact ?? raw.expectedValue ?? actor.expected_kpi_impact ?? ""),
    novelty,
    noveltyRationale: String(actor.novelty_assessment ?? raw.noveltyRationale ?? ""),
    confidence,
    sources: sourceStrings.length ? sourceStrings : sourceDetails.map((s) => s.title),
    sourceDetails,
    risks: {
      technical: String(actorRisks.technical ?? "Не оценено"),
      economic: String(actorRisks.economic ?? "Не оценено"),
    },
  };
}

export function roadmapResponseToModel(resp: RoadmapResponse): Roadmap {
  return {
    id: `roadmap-${resp.hypothesisId}`,
    hypothesisId: resp.hypothesisId,
    totalDuration: resp.totalDuration,
    totalResources: resp.totalResources,
    steps: resp.steps,
    sourceDetails: resp.sourceDetails,
  };
}

/** Merge hypothesis sources into roadmap when API omits them */
export function enrichRoadmapWithHypothesisSources(roadmap: Roadmap, hypothesis: Hypothesis): Roadmap {
  const sources = roadmap.sourceDetails?.length
    ? roadmap.sourceDetails
    : hypothesis.sourceDetails;
  if (!sources?.length) return roadmap;

  const steps = roadmap.steps.map((step, i) => ({
    ...step,
    sourceDetails: step.sourceDetails?.length
      ? step.sourceDetails
      : [sources[i % sources.length], sources[(i + 1) % sources.length]].filter(
          (s, idx, arr) => arr.findIndex((x) => x.chunkId === s.chunkId && x.title === s.title) === idx,
        ),
  }));

  return { ...roadmap, sourceDetails: sources, steps };
}

/** Parse markdown-ish experiment roadmap text into steps (fallback) */
export function parseRoadmapText(text: string, hypothesisId: string): Roadmap {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const steps: RoadmapStep[] = [];
  let order = 0;

  for (const line of lines) {
    const match = line.match(/^(\d+)[.)]\s*(.+)/);
    if (!match) continue;
    order += 1;
    steps.push({
      id: `s${order}`,
      order,
      title: match[2].slice(0, 120),
      description: match[2],
      resources: "—",
      duration: "—",
      successCriteria: "—",
      failureCriteria: "—",
      status: "pending",
    });
  }

  return {
    id: `roadmap-${hypothesisId}`,
    hypothesisId,
    totalDuration: steps.length ? `${steps.length} этапов` : "—",
    totalResources: "—",
    steps: steps.length
      ? steps
      : [
          {
            id: "s1",
            order: 1,
            title: "Лабораторная проверка",
            description: text.slice(0, 500) || "План проверки из отчёта LLM",
            resources: "—",
            duration: "—",
            successCriteria: "—",
            failureCriteria: "—",
            status: "pending",
          },
        ],
  };
}

export const USE_MOCK_API = import.meta.env.VITE_USE_MOCK !== "false";
