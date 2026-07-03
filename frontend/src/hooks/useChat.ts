import { useState, useCallback, useRef } from "react";
import type { ChatMessage, Hypothesis } from "@/types";

function generateId() {
  return Math.random().toString(36).substring(2, 10);
}

const DEMO_HYPOTHESES: Hypothesis[] = [
  {
    id: "h1",
    title: "Добавка 0.3% Nb в сплав X при отжиге 950°C",
    description:
      "Микролегирование ниобием в количестве 0.3% при температуре отжига 950°C с выдержкой 2 часа позволит повысить жаропрочность сплава X за счёт формирования дисперсных карбидов NbC.",
    rationale:
      "Карбиды ниобия (NbC) обладают высокой термодинамической стабильностью и температура их растворения (~1100°C) значительно выше температуры эксплуатации сплава. Дисперсные частицы NbC размером 10–50 нм эффективно блокируют движение дислокаций и границ зёрен при высоких температурах.",
    sources: [
      "Патент RU 2 7XX XXX: «Жаропрочный сплав на основе никеля»",
      "Smith et al., Materials Science and Engineering A, 2023",
    ],
    novelty: "high",
    risks: {
      technical: "Возможно образование грубых карбидов при отклонении режима отжига",
      economic: "Стоимость Nb ~$45/кг, увеличение себестоимости сплава на ~2%",
    },
    expectedValue: "Повышение жаропрочности на 15–18% при сохранении пластичности >8%",
    mechanism:
      "Дисперсионное упрочнение за счёт выделения наноразмерных карбидов NbC по границам и в теле зёрен",
  },
  {
    id: "h2",
    title: "Замена части Ni на Fe в шихте с корректировкой режима ТО",
    description:
      "Снижение содержания никеля в сплаве Y на 5% с замещением железом и оптимизацией режима термической обработки позволит снизить себестоимость шихты без потери прочностных характеристик.",
    rationale:
      "Железо и никель образуют непрерывный ряд твёрдых растворов. При содержании Fe до 20% в никелевых сплавах сохраняется ГЦК-структура. Корректировка режима старения компенсирует снижение объёмной доли γ'-фазы.",
    sources: [
      "ГОСТ 5632-72: «Стали высоколегированные и сплавы коррозионностойкие»",
      "Kozlov et al., Металловедение и термическая обработка металлов, 2024",
    ],
    novelty: "medium",
    risks: {
      technical: "Снижение коррозионной стойкости в агрессивных средах",
      economic: "Экономия ~8% на стоимости шихты при текущих ценах на Ni",
    },
    expectedValue: "Снижение себестоимости шихты на 7–9% при сохранении σв > 1200 МПа",
    mechanism:
      "Твердорастворное упрочнение Fe-Ni матрицы с компенсацией за счёт оптимизации режима дисперсионного твердения",
  },
];

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

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
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsGenerating(true);

      try {
        abortRef.current = new AbortController();

        const response = await fetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: "yandexgpt",
            messages: [
              {
                role: "system",
                content:
                  "Ты — ИИ-ассистент «Фабрики гипотез» Норникеля. Твоя задача — генерировать проверяемые научные гипотезы, анализировать материалы и помогать исследователям. Отвечай на русском языке, подробно и по делу.",
              },
              ...messages.map((m) => ({ role: m.role, content: m.content })),
              { role: "user", content: text },
            ],
          }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const content = data.choices?.[0]?.message?.content || "Нет ответа от модели";

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content, isStreaming: false, hypotheses: DEMO_HYPOTHESES }
              : m,
          ),
        );
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
                ? { ...m, content: `Ошибка: ${(err as Error).message}. Проверьте, запущен ли llm-service.`, isStreaming: false }
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
