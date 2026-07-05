import { useState, useCallback } from "react";
import { AppLayout } from "@/components/layout";
import { ChatContainer } from "@/components/chat";
import type { AgentNodeData } from "@/components/chat";
import { DocumentList, DocumentPreview, DocumentUploadModal } from "@/components/documents";
import { useChat, useDocuments } from "@/hooks";
import { AttentionView, ExpertSettingsModal } from "@/components/ui";
import type { ExpertSettings } from "@/hooks/useChat";
import { Lightbulb, MessageSquare, TrendingUp, Sparkles, Shield, FlaskConical, Map } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Document } from "@/types";

const SUGGESTIONS = [
  { icon: TrendingUp, color: "accent" as const, text: "Снизить потери никеля в хвостах флотации" },
  { icon: Sparkles, color: "blue" as const, text: "Повысить извлечение меди из труднообогатимых руд" },
  { icon: Shield, color: "green" as const, text: "Оптимизировать цикл измельчения для раскрытия сульфидов" },
  { icon: FlaskConical, color: "amber" as const, text: "Уменьшить переизмельчение целевых минералов" },
];

const colorMap = {
  accent: { bg: "bg-accent-bg", text: "text-accent", border: "border-accent-border" },
  blue: { bg: "bg-accent-blue-bg", text: "text-accent-blue", border: "border-accent-blue-border" },
  green: { bg: "bg-accent-green-bg", text: "text-accent-green", border: "border-accent-green-border" },
  amber: { bg: "bg-accent-amber-bg", text: "text-accent-amber", border: "border-accent-amber-border" },
};

const DEFAULT_SETTINGS: ExpertSettings = { hypothesisCount: 5, agentCycleDepth: 3, temperature: 0.7 };
const DEMO_HYPOTHESES: Hypothesis[] = [
  {
    id: "h1",
    title: "Магнитная сепарация надцелевого класса с последующим доизмельчением в отдельном цикле",
    description: "Выделение пирротина магнитной сепарацией из хвостов флотации с направлением магнитной фракции на доизмельчение (регринд) для вскрытия тонковкрапленного никеля.",
    rationale: "По данным минералогического анализа хвостов, статья потерь «Примесь в пирротине» составляет 81.1 т никеля. Пирротин обладает выраженными магнитными свойствами (магнитная восприимчивость 3–5×10⁻³ СГС), в отличие от цветных силикатов. Выделение магнитной фракции позволяет направить её на отдельный цикл доизмельчения, не переизмельчая при этом пустую породу основного потока. Это повышает раскрытие тонковкрапленных сульфидов никеля без снижения общей производительности фабрики.",
    sources: [
      "Патент RU 2 812 345 C1 «Способ доизмельчения магнитной фракции хвостов флотации», 2024",
      "Wills B.A., Mineral Processing Technology, 8th ed., Chapter 13: Magnetic Separation",
      "Внутренний отчёт ЛФ-2024-017: «Минералогический анализ хвостов флотации ТОФ»",
    ],
    novelty: "high",
    noveltyRationale: "Патентный поиск по Espacenet и Google Patents (2020–2025) показал только 2 релевантных патента по комбинации магнитной сепарации и регринда применительно к сульфидным рудам Норильского типа. Систематические исследования влияния напряжённости магнитного поля на извлечение пирротина из хвостов отсутствуют.",
    confidence: 0.85,
    risks: {
      technical: "Возможен захват немагнитных сростков в магнитную фракцию при напряжённости поля выше 0.5 Тл, что увеличит циркуляционную нагрузку. Требуется подбор оптимальной напряжённости.",
      economic: "Установка магнитного сепаратора — CAPEX ~$120K. Дополнительная мельница доизмельчения — CAPEX ~$350K. Окупаемость при текущих потерях Ni — 8 месяцев.",
    },
    expectedValue: "Снижение потерь никеля в хвостах на 25–30 т/год (+1.2% извлечения). Дополнительная прибыль ~$420K/год при текущих ценах на Ni.",
    mechanism: "Магнитная сепарация в слабом поле (0.3–0.5 Тл) извлекает пирротин, содержащий тонковкрапленный пентландит (Ni,Fe)₉S₈. Последующее доизмельчение магнитной фракции до -45 мкм вскрывает сульфидные включения для повторной флотации.",
  },
  {
    id: "h2",
    title: "Изменение геометрии футеровки шаровых мельниц для повышения тонины помола",
    description: "Замена стандартной волнистой футеровки на спирально-ступенчатую для увеличения доли ударного воздействия при измельчении, что повысит раскрытие сульфидов из силикатной матрицы.",
    rationale: "По данным таблицы потерь, наибольший вклад вносит статья «Силикатная форма/Валлериит» — 256.7 т никеля. Это свидетельствует о недостаточном раскрытии полезных минералов: пентландит и халькопирит остаются внутри силикатной породы. Изменение геометрии футеровки меняет траекторию падения шаров внутри мельницы — спирально-ступенчатый профиль увеличивает высоту подъёма шаровой загрузки на 15–20%, что повышает долю ударного (дробящего) воздействия относительно истирающего. Это особенно важно для руд с высокой долей силикатов.",
    sources: [
      "ГОСТ 7524-2015: «Шары мелющие стальные для шаровых мельниц»",
      "Austin L.G. et al., Minerals Engineering, 2022, v.180, «Effect of liner design on grinding efficiency»",
      "Технический паспорт мельницы МШЦ-4500×6000, цех измельчения ТОФ",
    ],
    novelty: "medium",
    noveltyRationale: "Влияние геометрии футеровки на раскрытие известно в литературе, но оптимизация профиля применительно к сульфидным рудам Норильского типа с высоким содержанием силикатов ранее систематически не исследовалась.",
    confidence: 0.72,
    risks: {
      technical: "Увеличение ударной нагрузки может повысить износ футеровки на 20–30% (сокращение срока службы с 8 до 6 месяцев). Риск повышенного намола металлического железа в пульпу, что может активировать пирротин и снизить селективность флотации.",
      economic: "Замена футеровки — CAPEX ~$180K. Дополнительные простои на замену — ~48 часов/год. Снижение срока службы футеровки — дополнительные OPEX ~$60K/год.",
    },
    expectedValue: "Снижение потерь никеля в силикатной форме на 40–60 т/год (+1.8% извлечения). Дополнительная прибыль ~$600K/год.",
    mechanism: "Спирально-ступенчатая футеровка увеличивает траекторию подъёма шаров, создавая каскадный режим с большей долей удара. Это разрушает силикатную матрицу по границам зёрен сульфидов, повышая степень раскрытия пентландита и халькопирита.",
  },
  {
    id: "h3",
    title: "Замена песковых насадок гидроциклонов с уменьшением диаметра с 12 мм до 8 мм",
    description: "Уменьшение диаметра песковой насадки (apex) гидроциклонов ГЦ-500 с 12 мм до 8 мм для увеличения плотности песков и возврата недоизмельчённого материала в мельницу.",
    rationale: "Высокие потери в силикатах и валлериите (256.7 т Ni) указывают на недостаточную классификацию: крупные сростки уходят в слив гидроциклонов и далее в хвосты. Уменьшение диаметра песковой насадки с 12 до 8 мм увеличивает противодавление и поднимает плотность песков (с 62% до 68–70% твёрдого), возвращая больше крупного и недоизмельчённого материала в мельницу. Это оперативный способ улучшить классификацию без капитальных затрат — замена насадок производится за 2–3 часа силами сменного персонала.",
    sources: [
      "Napier-Munn T.J. et al., Mineral Comminution Circuits, JKMRC, Chapter 9: Hydrocyclones",
      "Отчёт ОГМ-2024-089: «Анализ работы классифицирующего оборудования цеха измельчения»",
      "Техническая документация Krebs Engineers, Cyclone Sizing Guidelines, 2023",
    ],
    novelty: "low",
    noveltyRationale: "Методика является стандартной операционной практикой на обогатительных фабриках. Однако применение к конкретной руде ТОФ с учётом гранулометрического состава питания гидроциклонов ранее не оптимизировалось.",
    confidence: 0.91,
    risks: {
      technical: "Чрезмерное уменьшение диаметра насадки (ниже 8 мм) может привести к забиванию песковой насадки (roping) при колебаниях гранулометрии питания. Требуется мониторинг давления на входе гидроциклона (оптимум 60–80 кПа).",
      economic: "Стоимость одной насадки — ~$200. Замена на всех гидроциклонах секции — ~$2K. Проект окупается в течение первой недели после внедрения.",
    },
    expectedValue: "Снижение циркулирующей нагрузки на 10–15%, уменьшение выхода класса +71 мкм в сливе на 30%. Снижение потерь никеля ~15–20 т/год (+0.6% извлечения). Экономия ~$250K/год.",
    mechanism: "Уменьшенный apex создаёт более высокое центробежное ускорение в зоне разгрузки песков. Частицы крупнее граничного зерна с большей вероятностью отбрасываются к стенке и возвращаются в мельницу, а не уходят в слив.",
  },
  {
    id: "h4",
    title: "Полная замена спиральных классификаторов на гидроциклоны в цикле измельчения",
    description: "Замена спиральных классификаторов 1КСН-24 на гидроциклоны ГЦ-500 для повышения эффективности классификации и снижения переизмельчения тяжёлых сульфидов.",
    rationale: "Спиральные классификаторы разделяют частицы по крупности с низкой эффективностью (E = 40–60%), особенно для частиц плотностью выше 3 г/см³. Тяжёлые сульфиды никеля и меди (ρ = 4.5–5.0 г/см³) оседают в классификаторе быстрее лёгких силикатов и возвращаются в мельницу, где переизмельчаются до шламов (-10 мкм). Шламы теряются при флотации из-за низкой вероятности прилипания к пузырькам. Гидроциклоны разделяют по массовой крупности, обеспечивая эффективность E = 75–85%.",
    sources: [
      "King R.P., Modeling and Simulation of Mineral Processing Systems, 2nd ed., Chapter 5: Classification",
      "Проектная документация ТОФ, раздел «Измельчительно-классифицирующий цикл», 2019",
      "Metso Outotec, Grinding Circuit Optimization Guide, 2024",
    ],
    novelty: "low",
    noveltyRationale: "Замена классификаторов на гидроциклоны — типовая модернизация, реализованная на фабриках Norilsk, Kola MMC, а также на зарубежных аналогах. Однако проект требует полной остановки секции и значительных CAPEX.",
    confidence: 0.65,
    risks: {
      technical: "Необходимость полной остановки и перестройки секций фабрики (демонтаж классификаторов, монтаж зумпфов, насосов, гидроциклонов). Срок реализации — 6–8 месяцев на секцию. Риск несовместимости с существующей компоновкой цеха.",
      economic: "Огромные капитальные затраты: CAPEX ~$2.5M на секцию. Длительный период окупаемости — 3–4 года.",
    },
    expectedValue: "Снижение переизмельчения сульфидов на 40%, уменьшение выхода класса -10 мкм в питании флотации на 25%. Повышение извлечения Ni на 2.5%, Cu на 1.8%. Дополнительная прибыль ~$1.2M/год.",
    mechanism: "Гидроциклоны используют центробежную силу (до 200g) для разделения частиц. Более тяжёлые сульфидные частицы требуют меньшего размера для ухода в слив, что компенсирует разницу в плотности и предотвращает их переизмельчение.",
  },
  {
    id: "h5",
    title: "Грохота тонкого грохочения после 2-й стадии измельчения как альтернатива магнитной сепарации",
    description: "Установка грохотов тонкого грохочения (Derrick Stack Sizer, 100 мкм) после 2-й стадии измельчения для разделения по крупности вместо гидроциклонной классификации.",
    rationale: "Сульфиды меди и никеля имеют плотность 4.5–5.0 г/см³ против 2.7 г/см³ у силикатов. В гидроциклонах тяжёлые, но уже достаточно мелкие сульфиды уходят в пески (из-за высокой плотности) и возвращаются в мельницу, превращаясь в шламы. Грохочение разделяет частицы строго по геометрическому размеру, игнорируя плотность. Это предотвращает переизмельчение тяжёлых сульфидов — ключевую проблему текущего цикла.",
    sources: [
      "Derrick Corporation, Stack Sizer Technical Manual, 2023",
      "Valine S.B. et al., Minerals Engineering, 2023, v.195, «Fine screening vs hydrocyclones in grinding circuits»",
      "Патент US 11,456,789 B2 «Method for fine screening in sulfide mineral processing», 2024",
    ],
    novelty: "medium",
    noveltyRationale: "Технология тонкого грохочения широко применяется в железорудной промышленности, но опыт внедрения на сульфидных рудах ограничен 3–4 проектами в мире. Для норильских руд пилотных испытаний не проводилось.",
    confidence: 0.68,
    risks: {
      technical: "Сетки тонкого грохочения (100 мкм) быстро забиваются (blinding) на вязких сульфидных рудах, содержащих тальк и серпентин. Частота замены полиуретановых панелей — до 2 раз в неделю. Требуются испытания на стойкость к blinding.",
      economic: "CAPEX ~$900K на секцию. Высокие операционные затраты на замену ситовых панелей — ~$150K/год. Сложность эксплуатации — требуется выделенный персонал для обслуживания.",
    },
    expectedValue: "Полное исключение переизмельчения сульфидов. Повышение извлечения Ni на 3.0%, Cu на 2.5%. Дополнительная прибыль ~$1.5M/год при условии решения проблемы blinding.",
    mechanism: "Грохочение — единственный метод классификации, разделяющий частицы исключительно по геометрическому размеру. Частицы сульфидов, достигшие целевого размера (-100 мкм), немедленно выводятся из цикла, независимо от их плотности.",
  },
];

const AGENT_STAGES: { phase: "retrieve" | "generate" | "validate" | "done"; delay: number; nodes: number[] }[] = [
  { phase: "retrieve", delay: 0, nodes: [] },
  { phase: "generate", delay: 1500, nodes: [0] },
  { phase: "generate", delay: 3200, nodes: [1] },
  { phase: "validate", delay: 5500, nodes: [2] },
  { phase: "validate", delay: 7800, nodes: [3] },
  { phase: "done", delay: 10500, nodes: [4] },
];

const FULL_AGENT_NODES: AgentNodeData[] = [
  {
    id: "a1",
    agent: "generator",
    title: "Анализ минералогических данных хвостов: идентификация статей потерь",
    summary: "Извлечены ключевые статьи потерь Ni и Cu из таблицы хвостов. Основные источники: пирротин (81.1 т), силикаты/валлериит (256.7 т).",
    detail: "Выполнен структурный парсинг Excel-файла tailings_analysis.xlsx:\n\n• Определены колонки металлов: Элемент 28 (Ni) и Элемент 29 (Cu) по заголовкам «Содержание, %» и «Извлечение, %».\n\n• Выделены строки-категории по ключевым словам: «Силикатная форма/Валлериит», «Примесь в пирротине», «Пирит», с агрегацией данных по фракциям крупности.\n\n• Основные статьи потерь никеля:\n  - Силикатная форма/Валлериит: 256.7 т — труднообогатимые минералы и нераскрытые сростки.\n  - Примесь в пирротине: 81.1 т — тонковкрапленный пентландит в магнитном пирротине.\n  - Шламы (-10 мкм): переизмельчённые сульфиды.\n\n• Потери меди: аналогичная структура, но с большей долей в пирите.\n\nGraphRAG: обход графа знаний (онтология обогащения) на 2 hop от узлов LossForm → Mineral → Mechanism. Для пирротина выявлена связь с MagneticSeparation, для силикатов — с Regrinding и Classification.",
    timestamp: 1.8,
  },
  {
    id: "a2",
    agent: "generator",
    title: "Генерация гипотез: от статей потерь к технологическим решениям",
    summary: "Сгенерировано 5 гипотез, напрямую связанных со статьями потерь. 3 гипотезы используют физические принципы (магнетизм, плотность, крупность).",
    detail: "На основе выявленных статей потерь сгенерированы технологические гипотезы:\n\nГипотеза 1 (Магнитная сепарация + регринд): целевая статья — «Примесь в пирротине» (81.1 т Ni). Пирротин — магнитный минерал (χ = 3–5×10⁻³ СГС). Выделение магнитной фракции → доизмельчение → вскрытие пентландита. Оценка эффективности: магнитная восприимчивость пирротина на порядок выше, чем у силикатов.\n\nГипотеза 2 (Футеровка): целевая статья — «Силикатная форма/Валлериит» (256.7 т Ni). Проблема раскрытия: сульфиды внутри силикатной матрицы. Решение: изменение траектории шаров для увеличения ударного воздействия.\n\nГипотеза 3 (Насадки гидроциклонов): та же целевая статья. Оперативное решение: уменьшение apex с 12 до 8 мм увеличит возврат крупных сростков в мельницу.\n\nГипотезы 4 и 5 сгенерированы как альтернативные системные решения проблемы классификации, но имеют высокий CAPEX.",
    timestamp: 3.2,
  },
  {
    id: "a3",
    agent: "actor",
    title: "Верификация гипотезы 1: магнитная сепарация пирротина",
    summary: "Найдено 5 подтверждающих источников. Магнитная восприимчивость пирротина подтверждена экспериментально.",
    detail: "Верификация гипотезы 1 (Магнитная сепарация + регринд):\n\n• Поиск по внутренней базе НТЦ: отчёт ЛФ-2024-017 содержит прямые измерения магнитной восприимчивости пирротина из хвостов ТОФ — χ = 4.2×10⁻³ СГС (подтверждает принципиальную возможность магнитного выделения).\n\n• Патентный поиск (Espacenet, Google Patents): патент RU 2 812 345 C1 описывает способ доизмельчения магнитной фракции с последующей флотацией — прямое подтверждение концепции.\n\n• Google Scholar: запрос «magnetic separation pyrrhotite pentlandite regrind» — 28 результатов. Наиболее релевантная работа: Arvidson et al., Minerals Engineering, 2023 — показано увеличение извлечения Ni на 1.8% при магнитной сепарации хвостов.\n\n• Arxiv: 1 препринт 2024 года по CFD-моделированию магнитных сепараторов для сульфидных пульп.\n\n• Ссылки верифицированы: патент RU подтверждён через Роспатент, Arvidson — DOI валиден, журнал Q1.",
    timestamp: 5.5,
  },
  {
    id: "a4",
    agent: "judge",
    title: "Критика гипотезы 1: оценка по 5 метрикам",
    summary: "Метрики: 5/5 PASS. Замечание: оптимизация напряжённости магнитного поля критична для селективности.",
    detail: "Оценка гипотезы 1 по системе метрик Judge:\n\n1. Полнота обоснования (вес 0.5): PASS — механизм магнитного выделения описан количественно (χ пирротина = 4.2×10⁻³ СГС), режим доизмельчения (-45 мкм) обоснован данными о крупности вкрапленности пентландита.\n\n2. Наличие ссылок (блокирующая): PASS — 3 источника, все верифицированы (патент — Роспатент, статьи — DOI).\n\n3. Механизм + новизна (вес 0.3): PASS — физический механизм магнитной сепарации + регринда описан, патентный поиск подтверждает новизну подхода для норильских руд.\n\n4. Риски (блокирующая): PASS — идентифицирован риск захвата немагнитных сростков при превышении 0.5 Тл и экономический риск CAPEX.\n\n5. Ценность/KPI (вес 0.2): PASS — ожидаемый эффект +1.2% извлечения Ni, окупаемость 8 мес.\n\nКонтраргумент (Arvidson 2023): при содержании пирротина >15% в питании магнитная флокуляция может снизить эффективность последующей флотации. Рекомендация: добавить дефлокулянт (Na₂SiO₃) в цикл флотации после регринда. Учтено в дорожной карте — шаг 3а.",
    timestamp: 7.8,
  },
  {
    id: "a5",
    agent: "judge",
    title: "Финальный анализ: ранжирование и рекомендации",
    summary: "Гипотезы 3 и 1 приняты как Quick Wins. Гипотезы 4 и 5 отброшены из-за высокого CAPEX.",
    detail: "Финальное ранжирование гипотез по критериям: реализуемость, эффект, риски, CAPEX/OPEX.\n\nПРИНЯТЫ (Quick Wins):\n\n• Гипотеза 3 (насадки 12→8 мм) — РЕКОМЕНДОВАНА К НЕМЕДЛЕННОМУ ВНЕДРЕНИЮ. CAPEX ~$2K, окупаемость <1 недели. Эффект: +0.6% извлечения Ni. Реализация: 2–3 часа силами сменного персонала.\n\n• Гипотеза 1 (магнитная сепарация + регринд) — РЕКОМЕНДОВАНА К ОПЫТНО-ПРОМЫШЛЕННЫМ ИСПЫТАНИЯМ. CAPEX ~$470K, окупаемость 8 мес. Эффект: +1.2% извлечения Ni. Требуется: пилотная установка на 1 секции.\n\n• Гипотеза 2 (футеровка) — ПРИНЯТА К РАССМОТРЕНИЮ при следующей плановой замене футеровки. CAPEX ~$180K. Эффект: +1.8% извлечения Ni.\n\nОТКЛОНЕНЫ:\n\n• Гипотеза 4 (замена классификаторов) — ОТКЛОНЕНА. CAPEX ~$2.5M/секцию, остановка производства 6–8 месяцев, окупаемость 3–4 года. Нерентабельно при текущем горизонте планирования.\n\n• Гипотеза 5 (тонкое грохочение) — ОТКЛОНЕНА. Высокий риск blinding сеток на вязких рудах. Требуются длительные пилотные испытания (6+ месяцев) перед принятием решения о CAPEX ~$900K.",
    timestamp: 10.2,
  },
];

function EmptyChatState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-6 text-center max-w-md">
      <AttentionView
        icon={<Lightbulb size={40} />}
        title="Фабрика гипотез"
        description="Опишите технологическую проблему — система сгенерирует проверяемые гипотезы с обоснованием, источниками и дорожной картой."
        variant="accent"
        size="lg"
        blur
        gradient
      />
      <div className="grid grid-cols-1 gap-2 w-full">
        {SUGGESTIONS.map((s) => {
          const Icon = s.icon;
          const c = colorMap[s.color];
          return (
            <button
              key={s.text}
              onClick={() => onSuggestion(s.text)}
              className={`flex items-center gap-3 px-4 py-3 rounded-2xl border ${c.border} ${c.bg} ${c.text}
                text-sm text-left hover:brightness-95 transition-all duration-200 cursor-pointer`}
            >
              <Icon size={16} className="flex-shrink-0" />
              {s.text}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const DEFAULT_SETTINGS: ExpertSettings = { hypothesisCount: 5, agentCycleDepth: 3, temperature: 0.7 };

export default function App() {
  const { documents, uploading, addByUrl, addByFiles, removeDocument } = useDocuments();
  const [activeTab, setActiveTab] = useState<"chat" | "documents" | "roadmap">("chat");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [previewState, setPreviewState] = useState<{ doc: Document; mode: "info" | "file" | "content" } | null>(null);
  const [settings, setSettings] = useState<ExpertSettings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [settings, setSettings] = useState<ExpertSettings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [genPhase, setGenPhase] = useState<"retrieve" | "generate" | "validate" | "done" | undefined>();
  const [genNodes, setGenNodes] = useState<AgentNodeData[]>([]);
  const [hasGenerated, setHasGenerated] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = { id: generateId(), role: "user", content: text, timestamp: new Date() };
    const assistantMsg: ChatMessage = { id: generateId(), role: "assistant", content: "", timestamp: new Date(), isStreaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsGenerating(true);

    const startedAt = Date.now();
    const duration = 10500;

    const progressTimer = setInterval(() => {
      /** progress simulation */
    }, 200);

    for (const stage of AGENT_STAGES) {
      const elapsed = Date.now() - startedAt;
      const remaining = stage.delay - elapsed;
      if (remaining > 0) {
        await new Promise<void>((resolve) => {
          const check = setInterval(() => {
            if (Date.now() - startedAt >= stage.delay) {
              clearInterval(check);
              resolve();
            }
          }, 50);
        });
      }
      setGenPhase(stage.phase);
      if (stage.nodes.length > 0) {
        setGenNodes((prev) => {
          const existing = new Set(prev.map((n) => n.id));
          const toAdd = stage.nodes.map((i) => FULL_AGENT_NODES[i]).filter((n) => !existing.has(n.id));
          return [...prev, ...toAdd];
        });
      }
    }

    clearInterval(progressTimer);

    const reply = `На основе минералогического анализа хвостов и загруженных документов сгенерировано ${settings.hypothesisCount} гипотез. Основные статьи потерь никеля: силикатная форма/валлериит (256.7 т) и примесь в пирротине (81.1 т). Три гипотезы рекомендованы к внедрению, две отклонены по экономическим причинам. Подробное обоснование — в карточках ниже.`;

    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantMsg.id
          ? {
              ...m,
              content: reply,
              isStreaming: false,
              hypotheses: DEMO_HYPOTHESES.slice(0, settings.hypothesisCount),
            }
          : m,
      ),
    );

    const doneElapsed = Date.now() - startedAt;
    const remaining = duration - doneElapsed;
    if (remaining > 0) {
      await new Promise((r) => setTimeout(r, remaining));
    }
    setGenPhase(undefined);
    setGenNodes([]);
    setHasGenerated(true);
    setIsGenerating(false);
  }, [settings.hypothesisCount]);

  const sidebarContent = (() => {
    switch (activeTab) {
      case "chat":
        return (
          <AttentionView
            icon={<MessageSquare size={24} />}
            title="Диалог"
            description="Документы, добавленные в диалог, появятся здесь."
            variant="gray"
            size="sm"
            className="py-6"
          />
        );
      case "documents":
        return (
          <DocumentList
            documents={documents}
            onRemove={removeDocument}
            onClick={(doc) => setPreviewState({ doc, mode: "info" })}
            onPreview={(doc) => setPreviewState({ doc, mode: "file" })}
            emptyMessage="Загрузите документы через кнопку «+»"
          />
        );
      case "roadmap":
        return lastAssistantMsg?.content ? (
          <div className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1">
              Результат генерации
            </h3>
            <div className="prose prose-sm max-w-none dark:prose-invert
              prose-headings:text-text prose-p:text-text prose-li:text-text
              prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-xs
              prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-gray-100 prose-pre:rounded-xl prose-pre:border prose-pre:border-border
              dark:prose-code:bg-gray-800/50 dark:prose-pre:bg-gray-800/50">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {lastAssistantMsg.content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <AttentionView
            icon={<Map size={24} />}
            title="Роадмапа"
            description="Отправьте запрос — результат генерации появится здесь."
            variant="gray"
            size="sm"
            className="py-6"
          />
        );
      default:
        return null;
    }
  })();

  const detailContent = previewState ? (
    <DocumentPreview
      document={previewState.doc}
      mode={previewState.mode}
      onModeChange={(mode) => setPreviewState((prev) => prev ? { ...prev, mode } : null)}
      onClose={() => setPreviewState(null)}
    />
  ) : undefined;

  const handleSourceClick = useCallback((source: string) => {
    const matching = documents.find(
      (d) => source.includes(d.name) || d.name.includes(source.substring(0, 30)),
    );
    if (matching) {
      setPreviewState({ doc: matching, mode: "info" });
      return;
    }
    const urlMatch = source.match(/https?:\/\/\S+/);
    if (urlMatch) {
      addByUrl(urlMatch[0]);
      return;
    }
    const tempDoc: Document = {
      id: generateId(),
      name: source.length > 80 ? source.substring(0, 80) + "..." : source,
      type: "other",
      url: "",
      uploadedAt: new Date(),
      status: "ready",
      extractedContent: {
        title: source,
        markdown: source,
        text: source,
        excerpt: null,
        html: `<p>${source}</p>`,
        metadata: {
          title: null,
          description: null,
          author: null,
          siteName: null,
          language: null,
          canonicalUrl: null,
        },
        statusCode: null,
      },
    };
    setPreviewState({ doc: tempDoc, mode: "content" });
  }, [documents, addByUrl]);

  return (
    <>
      <AppLayout
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onAddDocument={() => setUploadModalOpen(true)}
        onSettingsClick={() => setSettingsOpen(true)}
        sidebarContent={sidebarContent}
        detailContent={detailContent}
      >
        <ChatContainer
          messages={messages}
          onSend={(text) => sendMessage(text, undefined, settings)}
          onAttach={() => setUploadModalOpen(true)}
          disabled={isGenerating}
          emptyState={<EmptyChatState onSuggestion={(text) => sendMessage(text)} />}
        />
      </AppLayout>

      <ExpertSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={setSettings}
      />

      <DocumentUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadByUrl={addByUrl}
        onUploadByFile={addByFiles}
        uploading={uploading}
      />

      <ExpertSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={setSettings}
      />
    </>
  );
}
