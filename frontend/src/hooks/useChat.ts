import { useState, useCallback, useRef } from "react";
import type { ChatMessage } from "@/types";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

export interface ExpertSettings {
  hypothesisCount: number;
  agentCycleDepth: number;
  temperature: number;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string, _docs?: unknown[], settings?: ExpertSettings) => {
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

        const body: Record<string, unknown> = {
          model: "yandexgpt",
          messages: [
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: text },
          ],
        };

        if (settings?.temperature != null) {
          body.temperature = settings.temperature;
        }

        const response = await fetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: abortRef.current.signal,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const content = data.choices?.[0]?.message?.content || "";

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
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: `**Ошибка:** ${(err as Error).message}`, isStreaming: false }
                : m,
            ),
          );
        }
      } finally {
        setIsGenerating(false);
        abortRef.current = null;
      }
    },
    [messages],
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, isGenerating, sendMessage, stopGeneration };
}
