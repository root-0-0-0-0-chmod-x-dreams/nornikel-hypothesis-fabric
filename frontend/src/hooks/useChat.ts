import { useState, useCallback, useRef, useEffect, type Dispatch, type SetStateAction } from "react";
import { flushSync } from "react-dom";
import type { AgentStep, ChatMessage, GenerationSettings, Hypothesis, HypothesisSource, Roadmap } from "@/types";
import type { StreamEvent } from "@/api/types";
import { hypothesesApi, mockApi, DEMO_AGENT_STAGES, DEMO_AGENT_NODES } from "@/api";
import {
  USE_MOCK_API,
  normalizeBackendHypothesis,
  parseRoadmapText,
  roadmapResponseToModel,
  enrichRoadmapWithHypothesisSources,
} from "@/lib/hypothesis";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const api = USE_MOCK_API ? mockApi : hypothesesApi;

function progressToAgentStep(event: StreamEvent): AgentStep {
  const elapsed = event.elapsedSeconds ?? 0;
  const stage = event.stage ?? "analyzing";
  const current = event.current;
  const total = event.total;

  const stageMeta: Record<
    NonNullable<StreamEvent["stage"]>,
    { agent: AgentStep["agent"]; title: string; summary: string }
  > = {
    analyzing: {
      agent: "generator",
      title: "Запуск пайплайна генерации",
      summary: event.message ?? "Инициализация сервисов…",
    },
    retrieving: {
      agent: "generator",
      title: "GraphRAG: поиск релевантных параграфов",
      summary: event.message ?? "Qdrant + граф знаний",
    },
    generating: {
      agent: "generator",
      title: "Generator: формирование гипотез",
      summary: event.message ?? (total ? `Генерация ${total} гипотез…` : "DeepSeek LLM…"),
    },
    validating: {
      agent: "actor",
      title: total
        ? `Actor → Judge · ${current ?? "?"}/${total}`
        : "Actor → Judge: валидация",
      summary: event.message ?? "Проверка обоснований и источников",
    },
    report: {
      agent: "judge",
      title: "Формирование отчёта",
      summary: event.message ?? "Сборка итогового результата",
    },
  };

  const meta = stageMeta[stage] ?? stageMeta.analyzing;
  return {
    id: `progress-${stage}`,
    agent: meta.agent,
    title: meta.title,
    summary: meta.summary,
    detail: event.message ?? "",
    timestamp: elapsed,
    status: "running",
  };
}

function bumpRunningStepTimestamps(steps: AgentStep[], elapsed?: number): AgentStep[] {
  if (elapsed == null) return steps;
  return steps.map((step) =>
    step.status === "running" ? { ...step, timestamp: elapsed } : step,
  );
}

function patchAssistantMessage(
  assistantMsgId: string,
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>,
  patch: (message: ChatMessage) => ChatMessage,
) {
  flushSync(() => {
    setMessages((prev) =>
      prev.map((m) => (m.id === assistantMsgId ? patch(m) : m)),
    );
  });
}

function upsertAgentStep(steps: AgentStep[], incoming: AgentStep): AgentStep[] {
  const next = steps.map((step) =>
    step.status === "running" && step.id !== incoming.id
      ? { ...step, status: "done" as const }
      : step,
  );
  const idx = next.findIndex((step) => step.id === incoming.id);
  if (idx >= 0) {
    next[idx] = incoming;
    return next;
  }
  return [...next, incoming];
}

function stageMessage(stage?: StreamEvent["stage"], message?: string): string {
  if (message) return message;
  switch (stage) {
    case "retrieving":
      return "GraphRAG: поиск релевантных параграфов в базе знаний…";
    case "generating":
      return "Generator: формирование гипотез…";
    case "validating":
      return "Actor → Judge: валидация гипотез…";
    case "report":
      return "Формирование итогового отчёта…";
    default:
      return "Анализирую данные и формирую гипотезы…";
  }
}

async function streamAgentPipeline(
  assistantMsgId: string,
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>,
  _settings: GenerationSettings,
  signal: AbortSignal,
): Promise<void> {
  const steps: AgentStep[] = [];
  let prevDelay = 0;

  for (let si = 0; si < DEMO_AGENT_STAGES.length; si++) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");

    const stage = DEMO_AGENT_STAGES[si];
    await sleep(stage.delay - prevDelay);
    prevDelay = stage.delay;

    for (const nodeIdx of stage.nodes) {
      const node = DEMO_AGENT_NODES[nodeIdx];
      steps.forEach((s) => {
        s.status = "done";
      });
      steps.push({
        ...node,
        status: stage.phase === "done" ? "done" : "running",
      });
    }

    if (stage.phase === "done") {
      steps.forEach((s) => {
        s.status = "done";
      });
    }

    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantMsgId
          ? {
              ...m,
              content: si === 0 ? "Анализирую данные и формирую гипотезы…" : m.content,
              agentSteps: [...steps],
              generationElapsed: stage.delay / 1000,
              isStreaming: true,
            }
          : m,
      ),
    );
  }
}

async function streamRealGeneration(
  assistantMsgId: string,
  text: string,
  settings: GenerationSettings,
  signal: AbortSignal,
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>,
): Promise<{
  hyps: Hypothesis[];
  retrievedParagraphs: HypothesisSource[];
}> {
  const hyps: Hypothesis[] = [];

  for await (const event of hypothesesApi.generateStream(
    {
      query: text,
      maxHypotheses: settings.maxHypotheses,
      agentCycleDepth: settings.agentCycleDepth,
      temperature: settings.temperature,
    },
    signal,
  )) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");

    if (event.type === "error") {
      throw new Error(event.message || "Ошибка генерации");
    }

    if (event.type === "agent_step" && event.step) {
      const step: AgentStep = {
        ...event.step,
        timestamp: event.elapsedSeconds ?? event.step.timestamp,
      };
      patchAssistantMessage(assistantMsgId, setMessages, (m) => ({
        ...m,
        content: stageMessage(undefined, step.summary),
        agentSteps: upsertAgentStep(m.agentSteps ?? [], step),
        generationElapsed: event.elapsedSeconds ?? m.generationElapsed,
        isStreaming: true,
      }));
      continue;
    }

    if (event.type === "progress") {
      const step = progressToAgentStep(event);
      patchAssistantMessage(assistantMsgId, setMessages, (m) => ({
        ...m,
        content: stageMessage(event.stage, event.message),
        agentSteps: upsertAgentStep(m.agentSteps ?? [], step),
        generationElapsed: event.elapsedSeconds ?? m.generationElapsed,
        isStreaming: true,
      }));
      continue;
    }

    if (event.type === "hypothesis" && event.hypothesis) {
      const normalized = event.hypothesis.sourceDetails?.length
        ? event.hypothesis
        : normalizeBackendHypothesis(event.hypothesis as unknown as Record<string, unknown>, hyps.length);
      hyps.push(normalized);
      patchAssistantMessage(assistantMsgId, setMessages, (m) => ({
        ...m,
        hypotheses: [...hyps],
        generationElapsed: event.elapsedSeconds ?? m.generationElapsed,
        isStreaming: true,
      }));
      continue;
    }

    if (event.type === "done") {
      if (event.hypotheses?.length) {
        hyps.splice(
          0,
          hyps.length,
          ...event.hypotheses.map((h, i) =>
            h.sourceDetails?.length ? h : normalizeBackendHypothesis(h as unknown as Record<string, unknown>, i),
          ),
        );
      }
      return {
        hyps,
        retrievedParagraphs: event.retrievedParagraphs ?? [],
      };
    }
  }

  return { hyps, retrievedParagraphs: [] };
}

export function useChat(settings: GenerationSettings) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [selectedHypothesis, setSelectedHypothesis] = useState<Hypothesis | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [retrievedParagraphs, setRetrievedParagraphs] = useState<HypothesisSource[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const tickRef = useRef<number | null>(null);
  const activeAssistantIdRef = useRef<string | null>(null);
  const generationStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isGenerating) {
      if (tickRef.current != null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
      return;
    }

    tickRef.current = window.setInterval(() => {
      const startedAt = generationStartedAtRef.current;
      const assistantId = activeAssistantIdRef.current;
      if (!startedAt || !assistantId) return;

      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId && m.isStreaming
            ? {
                ...m,
                generationElapsed: Math.max(m.generationElapsed ?? 0, elapsed),
                agentSteps: bumpRunningStepTimestamps(m.agentSteps ?? [], elapsed),
              }
            : m,
        ),
      );
    }, 1000);

    return () => {
      if (tickRef.current != null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
    };
  }, [isGenerating]);

  const loadRoadmap = useCallback(async (hypothesis: Hypothesis) => {
    setRoadmapLoading(true);
    try {
      const resp = await api.getRoadmap(hypothesis.id);
      const model = enrichRoadmapWithHypothesisSources(
        roadmapResponseToModel(resp),
        hypothesis,
      );
      setRoadmap(model);
    } catch (err) {
      console.error("roadmap_load_failed", err);
      const fallback = parseRoadmapText(
        hypothesis.mechanism || hypothesis.description,
        hypothesis.id,
      );
      setRoadmap(enrichRoadmapWithHypothesisSources(fallback, hypothesis));
    } finally {
      setRoadmapLoading(false);
    }
  }, []);

  const selectHypothesis = useCallback(
    (hypothesis: Hypothesis) => {
      setSelectedHypothesis(hypothesis);
      void loadRoadmap(hypothesis);
    },
    [loadRoadmap],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: USE_MOCK_API ? "" : "Анализирую данные и формирую гипотезы…",
        timestamp: new Date(),
        isStreaming: true,
        agentSteps: USE_MOCK_API
          ? []
          : [
              {
                id: "progress-analyzing",
                agent: "generator",
                title: "Запуск пайплайна генерации",
                summary: "Подключение к GraphRAG, Qdrant и LLM…",
                detail: "",
                timestamp: 0,
                status: "running",
              },
            ],
        generationElapsed: 0,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsGenerating(true);
      setHypotheses([]);
      setRoadmap(null);
      setRetrievedParagraphs([]);
      setSelectedHypothesis(null);

      try {
        abortRef.current = new AbortController();
        const signal = abortRef.current.signal;
        activeAssistantIdRef.current = assistantMsg.id;
        generationStartedAtRef.current = Date.now();

        let hyps: Hypothesis[] = [];
        let paragraphs: HypothesisSource[] = [];

        if (USE_MOCK_API) {
          await streamAgentPipeline(assistantMsg.id, setMessages, settings, signal);

          const result = await api.generate({
            query: text,
            maxHypotheses: settings.maxHypotheses,
          });
          hyps = result.hypotheses;
          paragraphs = result.retrievedParagraphs ?? [];
        } else {
          const result = await streamRealGeneration(
            assistantMsg.id,
            text,
            settings,
            signal,
            setMessages,
          );
          hyps = result.hyps;
          paragraphs = result.retrievedParagraphs;
        }

        setHypotheses(hyps);
        setRetrievedParagraphs(paragraphs);

        const intro = USE_MOCK_API
          ? `По запросу «${text}» сформировано ${hyps.length} проверяемых гипотез. Ниже — структурированный вывод с рисками, источниками и оценкой уверенности.`
          : `По запросу «${text}» сформировано ${hyps.length} проверяемых гипотез с привязкой к параграфам базы знаний.`;

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? {
                  ...m,
                  content: intro,
                  isStreaming: false,
                  hypotheses: hyps,
                  agentSteps: m.agentSteps?.map((s) => ({ ...s, status: "done" as const })),
                }
              : m,
          ),
        );

        if (hyps[0]) {
          selectHypothesis(hyps[0]);
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: "Генерация остановлена.", isStreaming: false }
                : m,
            ),
          );
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? {
                    ...m,
                    content: `Ошибка: ${(err as Error).message}. ${
                      USE_MOCK_API
                        ? "Проверьте mock API."
                        : "Проверьте hypothesis-factory."
                    }`,
                    isStreaming: false,
                  }
                : m,
            ),
          );
        }
      } finally {
        setIsGenerating(false);
        abortRef.current = null;
        activeAssistantIdRef.current = null;
        generationStartedAtRef.current = null;
      }
    },
    [selectHypothesis, settings],
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isGenerating,
    sendMessage,
    stopGeneration,
    hypotheses,
    selectedHypothesis,
    selectHypothesis,
    roadmap,
    roadmapLoading,
    retrievedParagraphs,
  };
}
