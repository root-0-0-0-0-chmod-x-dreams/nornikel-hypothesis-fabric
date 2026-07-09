import type {
  GenerateRequest,
  GenerateResponse,
  StreamEvent,
  RoadmapRequest,
  RoadmapResponse,
  FeedbackRequest,
  FeedbackResponse,
  HistoryResponse,
} from "./types";
import type { Hypothesis } from "@/types";
import { DEMO_RETRIEVED_PARAGRAPHS, KNOWLEDGE_BASE_DOCUMENTS } from "@/lib/knowledgeBase";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const DEMO_HYPOTHESES: Hypothesis[] = [
  {
    id: "h1",
    title: "Магнитная сепарация надцелевого класса с последующим доизмельчением в отдельном цикле",
    description: "Выделение пирротина магнитной сепарацией из хвостов флотации с направлением магнитной фракции на доизмельчение (регринд) для вскрытия тонковкрапленного никеля.",
    rationale: "По данным минералогического анализа хвостов, статья потерь «Примесь в пирротине» составляет 81.1 т никеля. Пирротин обладает выраженными магнитными свойствами (магнитная восприимчивость 3–5×10⁻³ СГС), в отличие от цветных силикатов.",
    sources: [
      "Патент RU 2 812 345 C1 «Способ доизмельчения магнитной фракции хвостов флотации», 2024",
      "Wills B.A., Mineral Processing Technology, 8th ed., Chapter 13: Magnetic Separation",
      "Внутренний отчёт ЛФ-2024-017: «Минералогический анализ хвостов флотации ТОФ»",
    ],
    novelty: "high",
    noveltyRationale: "Патентный поиск показал только 2 релевантных патента по комбинации магнитной сепарации и регринда для сульфидных руд Норильского типа.",
    confidence: 0.85,
    risks: {
      technical: "Возможен захват немагнитных сростков при напряжённости поля выше 0.5 Тл.",
      economic: "CAPEX ~$120K (сепаратор) + $350K (мельница). Окупаемость 8 месяцев.",
    },
    expectedValue: "Снижение потерь никеля на 25–30 т/год (+1.2% извлечения). Прибыль ~$420K/год.",
    mechanism: "Магнитная сепарация в слабом поле (0.3–0.5 Тл) извлекает пирротин с тонковкрапленным пентландитом. Доизмельчение до -45 мкм вскрывает сульфиды для повторной флотации.",
    sourceDetails: [DEMO_RETRIEVED_PARAGRAPHS[0], DEMO_RETRIEVED_PARAGRAPHS[1]],
  },
  {
    id: "h2",
    title: "Изменение геометрии футеровки шаровых мельниц для повышения тонины помола",
    description: "Замена волнистой футеровки на спирально-ступенчатую для увеличения доли ударного воздействия при измельчении.",
    rationale: "Наибольший вклад — «Силикатная форма/Валлериит» (256.7 т Ni). Спирально-ступенчатый профиль увеличивает высоту подъёма шаровой загрузки на 15–20%, повышая долю ударного воздействия.",
    sources: [
      "ГОСТ 7524-2015: «Шары мелющие стальные для шаровых мельниц»",
      "Austin L.G. et al., Minerals Engineering, 2022, v.180",
      "Технический паспорт мельницы МШЦ-4500×6000, цех измельчения ТОФ",
    ],
    novelty: "medium",
    noveltyRationale: "Оптимизация профиля для сульфидных руд Норильского типа ранее не исследовалась.",
    confidence: 0.72,
    risks: {
      technical: "Увеличение износа футеровки на 20–30%. Риск намола железа в пульпу.",
      economic: "CAPEX ~$180K. Дополнительные OPEX ~$60K/год.",
    },
    expectedValue: "Снижение потерь никеля на 40–60 т/год (+1.8% извлечения). Прибыль ~$600K/год.",
    mechanism: "Спирально-ступенчатая футеровка создаёт каскадный режим, разрушая силикатную матрицу по границам зёрен сульфидов.",
    sourceDetails: [DEMO_RETRIEVED_PARAGRAPHS[4], DEMO_RETRIEVED_PARAGRAPHS[0]],
  },
  {
    id: "h3",
    title: "Замена песковых насадок гидроциклонов с уменьшением диаметра с 12 мм до 8 мм",
    description: "Уменьшение apex гидроциклонов ГЦ-500 для увеличения плотности песков и возврата недоизмельчённого материала в мельницу.",
    rationale: "Крупные сростки уходят в слив и далее в хвосты. Уменьшение apex с 12 до 8 мм поднимает плотность песков с 62% до 68–70% твёрдого.",
    sources: [
      "Napier-Munn T.J. et al., Mineral Comminution Circuits, JKMRC, Chapter 9",
      "Отчёт ОГМ-2024-089: «Анализ работы классифицирующего оборудования»",
      "Krebs Engineers, Cyclone Sizing Guidelines, 2023",
    ],
    novelty: "low",
    noveltyRationale: "Стандартная практика, но для руды ТОФ ранее не оптимизировалась.",
    confidence: 0.91,
    risks: {
      technical: "Риск забивания (roping) при колебаниях гранулометрии. Требуется мониторинг давления.",
      economic: "Стоимость насадки ~$200. Замена на секции ~$2K. Окупаемость <1 недели.",
    },
    expectedValue: "Снижение циркулирующей нагрузки на 10–15%. Экономия ~$250K/год.",
    mechanism: "Уменьшенный apex создаёт более высокое центробежное ускорение, возвращая крупные частицы в мельницу.",
    sourceDetails: [DEMO_RETRIEVED_PARAGRAPHS[2], DEMO_RETRIEVED_PARAGRAPHS[3]],
  },
  {
    id: "h4",
    title: "Полная замена спиральных классификаторов на гидроциклоны в цикле измельчения",
    description: "Замена классификаторов 1КСН-24 на гидроциклоны ГЦ-500 для повышения эффективности классификации.",
    rationale: "Спиральные классификаторы имеют низкую эффективность (E = 40–60%) для частиц плотностью выше 3 г/см³. Гидроциклоны — E = 75–85%.",
    sources: [
      "King R.P., Modeling and Simulation of Mineral Processing Systems, 2nd ed.",
      "Проектная документация ТОФ, 2019",
      "Metso Outotec, Grinding Circuit Optimization Guide, 2024",
    ],
    novelty: "low",
    noveltyRationale: "Типовая модернизация, реализованная на ряде фабрик. Требует полной остановки секции.",
    confidence: 0.65,
    risks: {
      technical: "Остановка секции на 6–8 месяцев. Риск несовместимости с компоновкой цеха.",
      economic: "CAPEX ~$2.5M/секцию. Окупаемость 3–4 года.",
    },
    expectedValue: "Снижение переизмельчения на 40%. Повышение извлечения Ni на 2.5%. Прибыль ~$1.2M/год.",
    mechanism: "Гидроциклоны используют центробежную силу (до 200g). Тяжёлые сульфиды требуют меньшего размера для ухода в слив.",
  },
  {
    id: "h5",
    title: "Грохота тонкого грохочения после 2-й стадии измельчения как альтернатива магнитной сепарации",
    description: "Установка грохотов Derrick Stack Sizer (100 мкм) для разделения по геометрическому размеру вместо гидроциклонной классификации.",
    rationale: "Грохочение разделяет строго по размеру, игнорируя плотность. Предотвращает переизмельчение тяжёлых сульфидов.",
    sources: [
      "Derrick Corporation, Stack Sizer Technical Manual, 2023",
      "Valine S.B. et al., Minerals Engineering, 2023, v.195",
      "Патент US 11,456,789 B2, 2024",
    ],
    novelty: "medium",
    noveltyRationale: "Технология применяется в железорудной промышленности, для сульфидных руд — 3–4 проекта в мире.",
    confidence: 0.68,
    risks: {
      technical: "Быстрое забивание сеток (blinding) на вязких рудах. Замена панелей до 2 раз в неделю.",
      economic: "CAPEX ~$900K/секцию. OPEX ~$150K/год на замену панелей.",
    },
    expectedValue: "Полное исключение переизмельчения. Повышение извлечения Ni на 3.0%. Прибыль ~$1.5M/год.",
    mechanism: "Единственный метод классификации, разделяющий частицы исключительно по геометрическому размеру.",
  },
];

export const DEMO_AGENT_STAGES: { phase: "retrieve" | "generate" | "validate" | "done"; delay: number; nodes: number[] }[] = [
  { phase: "retrieve", delay: 0, nodes: [] },
  { phase: "generate", delay: 1500, nodes: [0] },
  { phase: "generate", delay: 3200, nodes: [1] },
  { phase: "validate", delay: 5500, nodes: [2] },
  { phase: "validate", delay: 7800, nodes: [3] },
  { phase: "done", delay: 10500, nodes: [4] },
];

export const DEMO_AGENT_NODES = [
  {
    id: "a1", agent: "generator" as const,
    title: "Анализ данных хвостов: идентификация статей потерь",
    summary: "Извлечены статьи потерь Ni и Cu. Основные: пирротин (81.1 т), силикаты/валлериит (256.7 т).",
    detail: "Структурный парсинг Excel tailings_analysis.xlsx. Колонки металлов: Ni и Cu. Категории: силикатная форма/валлериит, примесь в пирротине, пирит. GraphRAG: обход LossForm → Mineral → Mechanism на 2 hop.",
    timestamp: 1.8,
  },
  {
    id: "a2", agent: "generator" as const,
    title: "Генерация гипотез: от статей потерь к решениям",
    summary: "Сгенерировано 5 гипотез. 3 используют физические принципы (магнетизм, плотность, крупность).",
    detail: "Гипотеза 1: магнитная сепарация пирротина + регринд. Гипотеза 2: изменение футеровки для ударного раскрытия. Гипотеза 3: уменьшение apex гидроциклонов. Гипотезы 4 и 5: системные решения с высоким CAPEX.",
    timestamp: 3.2,
  },
  {
    id: "a3", agent: "actor" as const,
    title: "Верификация: магнитная сепарация пирротина",
    summary: "5 подтверждающих источников. χ пирротина = 4.2×10⁻³ СГС подтверждена.",
    detail: "Отчёт ЛФ-2024-017: прямые измерения χ. Патент RU 2 812 345 C1. Google Scholar: Arvidson 2023 — +1.8% извлечения Ni.",
    timestamp: 5.5,
  },
  {
    id: "a4", agent: "judge" as const,
    title: "Критика гипотезы 1: 5 метрик",
    summary: "5/5 PASS. Замечание: магнитная флокуляция при >15% пирротина.",
    detail: "Метрики: обоснование PASS, ссылки PASS, механизм PASS, риски PASS, KPI PASS.",
    timestamp: 7.8,
  },
  {
    id: "a5", agent: "judge" as const,
    title: "Финальное ранжирование",
    summary: "Гипотезы 3 и 1 — Quick Wins. 4 и 5 отклонены по CAPEX.",
    detail: "Приняты: гипотеза 3 (насадки, $2K), гипотеза 1 (магнитная сепарация, $470K), гипотеза 2 (футеровка, $180K).",
    timestamp: 10.2,
  },
];

const DEMO_ROADMAP_STEPS: RoadmapResponse["steps"] = [
    { id: "s1", order: 1, title: "Отбор пробы хвостов", description: "Отбор 2 т хвостов ТОФ, ситовый анализ, измерение магнитной восприимчивости", resources: "Пробоотборник, сита 45/71/100 мкм, измеритель χ", duration: "3 дня", successCriteria: "Ni ≥0.25% в пробе", failureCriteria: "Ni <0.15%", status: "pending" },
    { id: "s2", order: 2, title: "Магнитная сепарация", description: "Тесты при 0.2, 0.35, 0.5 Тл. Анализ выхода и содержания Ni", resources: "Магнитный сепаратор, весы, РФА", duration: "1 неделя", successCriteria: "Извлечение Ni ≥60%, выход ≤15%", failureCriteria: "Извлечение <40% или выход >25%", status: "pending" },
    { id: "s3", order: 3, title: "Доизмельчение магнитной фракции", description: "Измельчение до -45 мкм (80% класса). Контроль гранулометрии", resources: "Лабораторная мельница, сита", duration: "1 неделя", successCriteria: "80% класса -45 мкм", failureCriteria: "Переизмельчение >30% класса -10 мкм", status: "pending" },
    { id: "s4", order: 4, title: "Флотация доизмельчённого продукта", description: "Флотация с Na₂SiO₃ (500 г/т). Сравнение с базовым режимом", resources: "Флотомашина, реагенты", duration: "1 неделя", successCriteria: "Прирост извлечения Ni ≥1.0%", failureCriteria: "Прирост <0.5%", status: "pending" },
    { id: "s5", order: 5, title: "Анализ и рекомендации к ОПИ", description: "Статистический анализ, расчёт CAPEX/OPEX, рекомендации", resources: "Аналитик", duration: "1 неделя", successCriteria: "TECHNO-ECON отчёт, p < 0.05", failureCriteria: "p > 0.05", status: "pending" },
];

function roadmapWithSources(hypothesisId: string, sources: typeof DEMO_RETRIEVED_PARAGRAPHS): RoadmapResponse {
  return {
    hypothesisId,
    totalDuration: "4–6 недель",
    totalResources: "Магнитный сепаратор, шаровая мельница, флотомашина, 2 т хвостов ТОФ",
    sourceDetails: sources,
    steps: DEMO_ROADMAP_STEPS.map((step, i) => ({
      ...step,
      sourceDetails: sources.length
        ? [sources[i % sources.length], sources[(i + 1) % sources.length]].filter(
            (s, idx, arr) => arr.findIndex((x) => x.chunkId === s.chunkId) === idx,
          )
        : [],
    })),
  };
}

export const mockApi = {
  async generate(req: GenerateRequest): Promise<GenerateResponse> {
    await sleep(1500);
    return {
      query: req.query,
      hypotheses: DEMO_HYPOTHESES.slice(0, req.maxHypotheses || 5),
      contextDocuments: KNOWLEDGE_BASE_DOCUMENTS,
      retrievedParagraphs: DEMO_RETRIEVED_PARAGRAPHS,
      generatedAt: new Date().toISOString(),
    };
  },

  async *generateStream(req: GenerateRequest): AsyncGenerator<StreamEvent> {
    yield { type: "progress", stage: "analyzing" };
    await sleep(800);
    yield { type: "progress", stage: "generating", current: 1, total: req.maxHypotheses || 5 };
    await sleep(1200);
    const count = req.maxHypotheses || 5;
    for (let i = 0; i < Math.min(count, DEMO_HYPOTHESES.length); i++) {
      yield { type: "hypothesis", hypothesis: DEMO_HYPOTHESES[i] };
      await sleep(600);
    }
    yield { type: "done", total: Math.min(count, DEMO_HYPOTHESES.length) };
  },

  async getRoadmap(hypothesisId: string, _req?: RoadmapRequest): Promise<RoadmapResponse> {
    await sleep(800);
    const hyp = DEMO_HYPOTHESES.find((h) => h.id === hypothesisId);
    const sources = hyp?.sourceDetails?.length ? hyp.sourceDetails : DEMO_RETRIEVED_PARAGRAPHS;
    return roadmapWithSources(hypothesisId, sources);
  },

  async submitFeedback(hypothesisId: string, req: FeedbackRequest): Promise<FeedbackResponse> {
    await sleep(400);
    return {
      hypothesisId,
      status: req.status,
      recordedAt: new Date().toISOString(),
    };
  },

  async getHistory(_params?: { status?: string; limit?: number; offset?: number }): Promise<HistoryResponse> {
    await sleep(300);
    return {
      items: DEMO_HYPOTHESES.slice(0, 5).map((h) => ({
        id: h.id,
        title: h.title,
        query: "Снизить потери никеля в хвостах флотации",
        novelty: h.novelty,
        confidence: h.confidence || 0,
        feedbackStatus: null,
        createdAt: new Date().toISOString(),
      })),
      total: 5,
      limit: 20,
      offset: 0,
    };
  },
};
