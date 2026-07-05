import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { ChatContainer } from "@/components/chat";
import { DocumentList, DocumentPreview, DocumentUploadModal } from "@/components/documents";
import { RoadmapView } from "@/components/roadmap";
import { useChat, useDocuments } from "@/hooks";
import { AttentionView, ExpertSettingsModal } from "@/components/ui";
import type { ExpertSettings } from "@/hooks/useChat";
import { Lightbulb, MessageSquare, TrendingUp, Sparkles, Shield, FlaskConical } from "lucide-react";
import type { Document, Roadmap } from "@/types";

const DEMO_ROADMAP: Roadmap = {
  id: "r1",
  hypothesisId: "h1: Добавка 0.3% Nb в сплав X",
  totalDuration: "6–8 недель",
  totalResources: "Плавильная печь, разрывная машина, металлографический микроскоп, 50 кг шихты",
  steps: [
    { id: "s1", order: 1, title: "Выплавка опытных образцов", description: "Выплавка 3 плавок сплава X с содержанием Nb 0.1%, 0.3%, 0.5% в вакуумной индукционной печи", resources: "Вакуумная индукционная печь, шихтовые материалы, 2 смены", duration: "1 неделя", successCriteria: "Получены слитки без видимых дефектов, химсостав в допуске ±0.02%", failureCriteria: "Отклонение химсостава >0.05%", status: "pending" },
    { id: "s2", order: 2, title: "Термическая обработка", description: "Отжиг при 950°C / 2 ч с закалкой в масло, старение при 750°C / 16 ч", resources: "Камерная печь с защитной атмосферой, закалочный бак", duration: "2 недели", successCriteria: "Твёрдость 38–42 HRC", failureCriteria: "Разброс твёрдости >3 HRC", status: "pending" },
    { id: "s3", order: 3, title: "Механические испытания при 800°C", description: "Испытания на длительную прочность при 800°C / 200 МПа", resources: "Разрывная машина, 9 образцов", duration: "2 недели", successCriteria: "Повышение времени до разрушения >12%", failureCriteria: "Разрушение ранее 100 ч", status: "pending" },
    { id: "s4", order: 4, title: "Микроструктурный анализ", description: "ПЭМ и РЭМ анализ карбидов NbC", resources: "ПЭМ, РЭМ, 6 шлифов", duration: "1–2 недели", successCriteria: "Размер карбидов 10–50 нм", failureCriteria: "Карбиды >200 нм", status: "pending" },
    { id: "s5", order: 5, title: "Анализ и отчёт", description: "Статистический анализ, подготовка отчёта", resources: "Аналитик, 1 неделя", duration: "1 неделя", successCriteria: "Отчёт по ГОСТ 7.32", failureCriteria: "p > 0.05", status: "pending" },
  ],
};

const SUGGESTIONS = [
  { icon: TrendingUp, color: "accent" as const, text: "Повысить жаропрочность сплава на 15%" },
  { icon: Sparkles, color: "blue" as const, text: "Снизить себестоимость шихты без потери прочности" },
  { icon: Shield, color: "green" as const, text: "Увеличить коррозионную стойкость" },
  { icon: FlaskConical, color: "amber" as const, text: "Оптимизировать режим термообработки" },
];

const colorMap = {
  accent: { bg: "bg-accent-bg", text: "text-accent", border: "border-accent-border" },
  blue: { bg: "bg-accent-blue-bg", text: "text-accent-blue", border: "border-accent-blue-border" },
  green: { bg: "bg-accent-green-bg", text: "text-accent-green", border: "border-accent-green-border" },
  amber: { bg: "bg-accent-amber-bg", text: "text-accent-amber", border: "border-accent-amber-border" },
};

function EmptyChatState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-6 text-center max-w-md">
      <AttentionView
        icon={<Lightbulb size={40} />}
        title="Фабрика гипотез"
        description="Опишите целевую технологическую проблему — система сгенерирует проверяемые гипотезы с обоснованием, ссылками на источники и дорожной картой проверки."
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
  const { messages, isGenerating, sendMessage } = useChat();
  const { documents, uploading, addByUrl, addByFiles, removeDocument } = useDocuments();
  const [activeTab, setActiveTab] = useState<"chat" | "documents" | "roadmap">("chat");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [previewState, setPreviewState] = useState<{ doc: Document; mode: "info" | "file" | "content" } | null>(null);
  const [settings, setSettings] = useState<ExpertSettings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const sidebarContent = (() => {
    switch (activeTab) {
      case "chat":
        return (
          <AttentionView
            icon={<MessageSquare size={24} />}
            title="Диалог"
            description="Документы, добавленные в диалог, появятся здесь. Перейдите во вкладку «Документы» для управления файлами."
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
        onSettingsClick={() => setSettingsOpen(true)}
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
          onSend={(text) => sendMessage(text, undefined, settings)}
          onAttach={() => setUploadModalOpen(true)}
          disabled={isGenerating}
          emptyState={<EmptyChatState onSuggestion={sendMessage} />}
        />
      </AppLayout>

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
