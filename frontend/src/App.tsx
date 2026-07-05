import { useState } from "react";
import { AppLayout } from "@/components/layout";
import { ChatContainer } from "@/components/chat";
import { DocumentList, DocumentPreview, DocumentUploadModal } from "@/components/documents";
import { useChat, useDocuments } from "@/hooks";
import { AttentionView, ExpertSettingsModal } from "@/components/ui";
import type { ExpertSettings } from "@/hooks/useChat";
import { Lightbulb, MessageSquare, TrendingUp, Sparkles, Shield, FlaskConical, Map } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Document } from "@/types";

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

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");

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
          emptyState={<EmptyChatState onSuggestion={(text) => sendMessage(text)} />}
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
