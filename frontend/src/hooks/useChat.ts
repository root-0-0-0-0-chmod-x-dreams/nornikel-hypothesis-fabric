import { useState, useCallback, useRef } from "react";
import type { ChatMessage, Document } from "@/types";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

export interface ExpertSettings {
  hypothesisCount: number;
  agentCycleDepth: number;
  temperature: number;
}

function buildSystemPrompt(docs: Document[], settings: ExpertSettings): string {
  const parts = [
    "Ты — ИИ-ассистент «Фабрики гипотез» Норникеля.",
    "Твоя задача — анализировать предоставленные документы, генерировать проверяемые научные и инженерные гипотезы, ранжировать их по новизне, рискам и ожидаемой ценности.",
    "",
    `Сгенерируй ровно **${settings.hypothesisCount}** гипотез.`,
    `Используй цикл проверки глубиной **${settings.agentCycleDepth}**: Generator → Actor ↔ Judge.`,
    "Для каждой гипотезы укажи: формулировку, научное обоснование, механизм влияния, источники, новизну (high/medium/low), технические и экономические риски, ожидаемую ценность.",
    "После списка гипотез добавь раздел «## Ранжирование» с распределением на Quick Wins и отклонённые.",
    "",
    "Отвечай на русском языке. Используй Markdown для форматирования: заголовки ###, списки, **жирный**, код.",
  ];

  const readyDocs = docs.filter((d) => d.status === "ready" && d.extractedContent?.markdown);
  if (readyDocs.length > 0) {
    parts.push("\n## Загруженные документы\n");
    for (const doc of readyDocs) {
      const content = doc.extractedContent!;
      parts.push(`### ${doc.name}\n\n${content.markdown.substring(0, 8000)}\n`);
    }
  }

  return parts.join("\n");
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [settings, setSettings] = useState<ExpertSettings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string, docs: Document[] = [], settings: ExpertSettings = { hypothesisCount: 5, agentCycleDepth: 3, temperature: 0.7 }) => {
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsGenerating(true);

      try {
        abortRef.current = new AbortController();
        const systemPrompt = buildSystemPrompt(docs, settings);

        const response = await fetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: "yandexgpt",
            temperature: settings.temperature,
            messages: [
              { role: "system", content: systemPrompt },
              ...messages.map((m) => ({ role: m.role, content: m.content })),
              { role: "user", content: text },
            ],
          }),
          signal,
        });

        if (response.ok) {
          const data = await response.json();
          const reply = data.choices?.[0]?.message?.content || "";

        const data = await response.json();
        const content = data.choices?.[0]?.message?.content || "Нет ответа от модели";

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content, isStreaming: false }
              : m,
          ),
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: "_Генерация остановлена._", isStreaming: false }
                : m,
            ),
          );
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMsg.id ? { ...m, content: "Генерация остановлена.", isStreaming: false } : m)),
          );
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: `**Ошибка:** ${(err as Error).message}. Проверьте, запущен ли llm-service.`, isStreaming: false }
                : m,
            ),
          );
        }
      } finally {
        setIsGenerating(false);
        abortRef.current = null;
      }
    },
    [settings],
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isGenerating,
    sendMessage,
    stopGeneration,
    settings,
    setSettings,
    settingsOpen,
    setSettingsOpen,
    agentReasoning: AGENT_REASONING,
    demoHypotheses: DEMO_HYPOTHESES,
  };
}
