import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { ChatContainer } from "@/components/chat";
import { DocumentPreview, DocumentUploadModal, ContextPanel } from "@/components/documents";
import { RoadmapView } from "@/components/roadmap";
import { RoadmapTimeline } from "@/components/roadmap/RoadmapTimeline";
import { ExpertSettingsModal } from "@/components/settings/ExpertSettingsModal";
import { useChat, useDocuments } from "@/hooks";
import { AttentionView, Spinner } from "@/components/ui";
import { canPreviewDocument, defaultPreviewMode } from "@/lib/knowledgeBase";
import type { GenerationSettings } from "@/types";
import { Lightbulb, Map, TrendingUp, Sparkles, Shield, FlaskConical } from "lucide-react";

const DEFAULT_SETTINGS: GenerationSettings = {
  maxHypotheses: 2,
  agentCycleDepth: 2,
  temperature: 0.4,
};

const SUGGESTIONS = [
  { icon: TrendingUp, color: "accent" as const, text: "Снизить потери никеля в хвостах флотации ТОФ" },
  { icon: Sparkles, color: "blue" as const, text: "Повысить извлечение меди без роста CAPEX" },
  { icon: Shield, color: "green" as const, text: "Снизить переизмельчение пирротина в цикле" },
  { icon: FlaskConical, color: "amber" as const, text: "Оптимизировать режим гидроциклонной классификации" },
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

export default function App() {
  const [settings, setSettings] = useState<GenerationSettings>(DEFAULT_SETTINGS);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const {
    messages,
    isGenerating,
    sendMessage,
    selectedHypothesis,
    selectHypothesis,
    roadmap,
    roadmapLoading,
    retrievedParagraphs,
  } = useChat(settings);
  const { knowledgeDocuments, userDocuments, uploading, addByUrl, addByFiles, removeDocument } = useDocuments();
  const [activeTab, setActiveTab] = useState<"chat" | "documents" | "roadmap">("chat");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [previewState, setPreviewState] = useState<{ doc: import("@/types").Document; mode: "info" | "file" | "content" } | null>(null);

  const openDocumentPreview = (doc: import("@/types").Document, mode?: "info" | "file" | "content") => {
    setPreviewState({ doc, mode: mode ?? defaultPreviewMode(doc) });
  };

  const sidebarContent = (() => {
    switch (activeTab) {
      case "chat":
        return (
          <ContextPanel
            knowledgeDocuments={knowledgeDocuments}
            userDocuments={userDocuments}
            retrievedParagraphs={retrievedParagraphs}
            onRemove={removeDocument}
            onClick={(doc) => openDocumentPreview(doc)}
            onPreview={(doc) => openDocumentPreview(doc, canPreviewDocument(doc) ? defaultPreviewMode(doc) : "info")}
          />
        );
      case "documents":
        return (
          <ContextPanel
            knowledgeDocuments={knowledgeDocuments}
            userDocuments={userDocuments}
            retrievedParagraphs={retrievedParagraphs}
            onRemove={removeDocument}
            onClick={(doc) => openDocumentPreview(doc)}
            onPreview={(doc) => openDocumentPreview(doc, canPreviewDocument(doc) ? defaultPreviewMode(doc) : "info")}
          />
        );
      case "roadmap":
        if (!selectedHypothesis) {
          return (
            <AttentionView
              icon={<Map size={24} />}
              title="Роадмапа"
              description="Сначала сгенерируйте гипотезы в чате — здесь появится план лабораторной проверки."
              variant="gray"
              size="sm"
              className="py-6"
            />
          );
        }
        return (
          <div className="flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1">
              Гипотеза
            </h3>
            <p className="text-sm text-text leading-relaxed px-1">{selectedHypothesis.title}</p>
            {roadmapLoading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : roadmap ? (
              <div className="flex flex-col gap-3">
                <RoadmapTimeline steps={roadmap.steps} />
                {roadmap.sourceDetails && roadmap.sourceDetails.length > 0 && (
                  <div className="px-1 pt-2 border-t border-border">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted mb-2">
                      Источники
                    </p>
                    <div className="space-y-1">
                      {roadmap.sourceDetails.slice(0, 3).map((s, i) => (
                        <p key={`${s.chunkId}-${i}`} className="text-[11px] text-accent leading-snug">
                          {s.title}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-text-muted px-1">Роадмапа не загружена</p>
            )}
          </div>
        );
      default:
        return null;
    }
  })();

  const mainContent = (() => {
    if (activeTab === "roadmap") {
      if (!selectedHypothesis || !roadmap) {
        return (
          <div className="flex items-center justify-center h-full p-8">
            <AttentionView
              icon={<Map size={32} />}
              title="Дорожная карта проверки"
              description="Отправьте запрос в чате и выберите гипотезу — здесь откроется полный план экспериментов с ресурсами и критериями успеха."
              variant="accent"
              size="md"
            />
          </div>
        );
      }
      return (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            <RoadmapView roadmap={roadmap} hypothesisTitle={selectedHypothesis.title} />
          </div>
        </div>
      );
    }

    return (
      <ChatContainer
        messages={messages}
        onSend={sendMessage}
        onAttach={() => setUploadModalOpen(true)}
        disabled={isGenerating}
        selectedHypothesisId={selectedHypothesis?.id}
        onSelectHypothesis={(h) => {
          selectHypothesis(h);
        }}
        generationSettings={{
          maxHypotheses: settings.maxHypotheses,
          agentCycleDepth: settings.agentCycleDepth,
        }}
        emptyState={<EmptyChatState onSuggestion={sendMessage} />}
      />
    );
  })();

  return (
    <>
      <AppLayout
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onAddDocument={() => setUploadModalOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        sidebarContent={sidebarContent}
        detailContent={
          previewState ? (
            <DocumentPreview
              document={previewState.doc}
              mode={previewState.mode}
              onModeChange={(mode) => setPreviewState((prev) => (prev ? { ...prev, mode } : null))}
              onClose={() => setPreviewState(null)}
            />
          ) : undefined
        }
      >
        {mainContent}
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
        onSave={setSettings}
      />
    </>
  );
}
