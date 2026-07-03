import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { ChatContainer } from "@/components/chat";
import { DocumentList, DocumentPreview, DocumentUploadModal } from "@/components/documents";
import { RoadmapView } from "@/components/roadmap";
import { useChat, useDocuments } from "@/hooks";
import { Lightbulb, MessageSquare } from "lucide-react";
import type { Document, Roadmap } from "@/types";

const DEMO_ROADMAP: Roadmap = {
  id: "r1",
  hypothesisId: "h1: Добавка 0.3% Nb в сплав X",
  totalDuration: "6–8 недель",
  totalResources: "Плавильная печь, разрывная машина, металлографический микроскоп, 50 кг шихты",
  steps: [
    {
      id: "s1", order: 1,
      title: "Выплавка опытных образцов",
      description: "Выплавка 3 плавок сплава X с содержанием Nb 0.1%, 0.3%, 0.5% в вакуумной индукционной печи",
      resources: "Вакуумная индукционная печь, шихтовые материалы, 2 смены",
      duration: "1 неделя",
      successCriteria: "Получены слитки без видимых дефектов, химсостав в допуске ±0.02%",
      failureCriteria: "Отклонение химсостава >0.05%, наличие усадочных раковин >2 мм",
      status: "pending",
    },
    {
      id: "s2", order: 2,
      title: "Термическая обработка",
      description: "Отжиг при 950°C / 2 ч с закалкой в масло, старение при 750°C / 16 ч для всех плавок",
      resources: "Камерная печь с защитной атмосферой, закалочный бак",
      duration: "2 недели",
      successCriteria: "Твёрдость в диапазоне 38–42 HRC, отсутствие обезуглероженного слоя >0.1 мм",
      failureCriteria: "Разброс твёрдости >3 HRC по сечению образца",
      status: "pending",
    },
    {
      id: "s3", order: 3,
      title: "Механические испытания при 800°C",
      description: "Испытания на длительную прочность при 800°C / 200 МПа",
      resources: "Разрывная машина с высокотемпературной печью, 9 образцов",
      duration: "2 недели",
      successCriteria: "Повышение времени до разрушения на >12% относительно базового состава",
      failureCriteria: "Разрушение ранее 100 ч, относительное удлинение <5%",
      status: "pending",
    },
    {
      id: "s4", order: 4,
      title: "Микроструктурный анализ",
      description: "ПЭМ и РЭМ анализ образцов для оценки размера и распределения карбидов NbC",
      resources: "Просвечивающий электронный микроскоп, растровый микроскоп, 6 шлифов",
      duration: "1–2 недели",
      successCriteria: "Размер карбидов NbC 10–50 нм, равномерное распределение",
      failureCriteria: "Образование грубых карбидов >200 нм, неравномерное распределение",
      status: "pending",
    },
    {
      id: "s5", order: 5,
      title: "Анализ и отчёт",
      description: "Статистический анализ результатов, подготовка отчёта и рекомендаций",
      resources: "Аналитик, 1 неделя рабочего времени",
      duration: "1 неделя",
      successCriteria: "Подтверждена/опровергнута гипотеза, оформлен отчёт по ГОСТ 7.32",
      failureCriteria: "Статистическая незначимость различий (p > 0.05)",
      status: "pending",
    },
  ],
};

function EmptyChatState() {
  return (
    <div className="flex flex-col items-center gap-4 text-center max-w-sm">
      <div className="p-4 rounded-2xl bg-accent-bg">
        <Lightbulb size={32} className="text-accent" />
      </div>
      <h2 className="text-lg font-semibold text-text">Фабрика гипотез</h2>
      <p className="text-sm text-text-muted leading-relaxed">
        Опишите целевую технологическую проблему, и я сгенерирую проверяемые гипотезы
        с обоснованием, ссылками на источники и дорожной картой проверки.
      </p>
      <div className="flex flex-wrap gap-2 justify-center mt-2">
        {[
          "Повысить жаропрочность сплава на 15%",
          "Снизить себестоимость шихты без потери прочности",
          "Увеличить коррозионную стойкость в агрессивных средах",
        ].map((suggestion) => (
          <span key={suggestion} className="px-3 py-1.5 text-xs bg-gray-100 rounded-full text-text-muted">
            {suggestion}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const { messages, isGenerating, sendMessage } = useChat();
  const { documents, uploading, addByUrl, addByFiles, removeDocument } = useDocuments();
  const [activeTab, setActiveTab] = useState<"chat" | "documents" | "roadmap">("chat");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [previewState, setPreviewState] = useState<{ doc: Document; mode: "info" | "file" } | null>(null);

  const sidebarContent = (() => {
    switch (activeTab) {
      case "chat":
        return (
          <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
            <MessageSquare size={28} className="text-text-muted/30" />
            <p className="text-sm text-text-muted">
              Документы, добавленные в диалог, появятся здесь.
            </p>
            <p className="text-xs text-text-muted/60">
              Перейдите во вкладку «Документы» для управления файлами.
            </p>
          </div>
        );
      case "documents":
        return (
          <DocumentList
            documents={documents}
            onRemove={removeDocument}
            onClick={(doc) => setPreviewState({ doc, mode: "info" })}
            onPreview={(doc) => setPreviewState({ doc, mode: "file" })}
            emptyMessage="Нет загруженных документов"
          />
        );
      case "roadmap":
        return (
          <div className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1">
              Гипотеза
            </h3>
            <p className="text-sm text-text leading-relaxed px-1">
              Добавка 0.3% Nb в сплав X при отжиге 950°C
            </p>
            <RoadmapView roadmap={DEMO_ROADMAP} />
          </div>
        );
      default:
        return null;
    }
  })();

  return (
    <>
      <AppLayout
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onAddDocument={() => setUploadModalOpen(true)}
        sidebarContent={sidebarContent}
        detailContent={
          previewState ? (
            <DocumentPreview
              document={previewState.doc}
              mode={previewState.mode}
              onModeChange={(mode) => setPreviewState((prev) => prev ? { ...prev, mode } : null)}
              onClose={() => setPreviewState(null)}
            />
          ) : undefined
        }
      >
        <ChatContainer
          messages={messages}
          onSend={sendMessage}
          onAttach={() => setUploadModalOpen(true)}
          disabled={isGenerating}
          emptyState={<EmptyChatState />}
        />
      </AppLayout>

      <DocumentUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadByUrl={addByUrl}
        onUploadByFile={addByFiles}
        uploading={uploading}
      />
    </>
  );
}
