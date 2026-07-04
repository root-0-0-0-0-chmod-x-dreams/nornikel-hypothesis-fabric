import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, FileText, Globe, ExternalLink, Clock, HardDrive, Info, Eye, FileCode } from "lucide-react";
import { Badge, Tabs, AttentionView, Progress } from "@/components/ui";
import type { Document } from "@/types";

type PreviewMode = "info" | "file" | "content";

interface DocumentPreviewProps {
  document: Document;
  mode: PreviewMode;
  onModeChange: (mode: PreviewMode) => void;
  onClose: () => void;
}

function formatSize(bytes?: number): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

function formatDate(date: Date): string {
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const typeLabels: Record<string, string> = {
  pdf: "PDF документ",
  docx: "Word документ",
  xlsx: "Excel таблица",
  url: "Внешняя ссылка",
  image: "Изображение",
  other: "Файл",
};

function isRealUrl(url: string): boolean {
  return url.length > 0 && url !== "#" && (url.startsWith("http://") || url.startsWith("https://"));
}

const previewableBlobTypes = ["pdf", "image"];

function ProcessingState() {
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const startedAt = Date.now();
    timerRef.current = setInterval(() => {
      setProgress(Math.min(92, Math.round(((Date.now() - startedAt) / 15000) * 92)));
    }, 200);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="flex flex-col items-center gap-5 py-6">
      <AttentionView
        icon={<Clock size={32} />}
        title="Идёт обработка"
        description="Извлечение текста, структурирование и индексация."
        variant="amber"
        size="md"
      />
      <div className="w-3/4 max-w-[200px]">
        <Progress value={progress} size="sm" color="amber" showValue />
      </div>
    </div>
  );
}

export function DocumentPreview({ document: doc, mode, onModeChange, onClose }: DocumentPreviewProps) {
  const isUrl = doc.type === "url";
  const hasRealUrl = isRealUrl(doc.url);
  const canPreviewFile = doc.blobUrl && previewableBlobTypes.includes(doc.type);
  const hasExtractedContent = !!doc.extractedContent;
  const content = doc.extractedContent;

  const viewTabs = [
    { id: "info", label: "Инфо", icon: <Info size={14} /> },
    ...(hasExtractedContent ? [{ id: "content" as const, label: "Контент", icon: <FileCode size={14} /> }] : []),
    ...(canPreviewFile ? [{ id: "file" as const, label: "Файл", icon: <Eye size={14} /> }] : []),
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-border flex-shrink-0 glass-strong">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`p-2 rounded-xl ${isUrl ? "bg-accent-blue-bg" : "bg-gray-100"} flex-shrink-0`}>
              {isUrl ? (
                <Globe size={18} className="text-accent-blue" />
              ) : (
                <FileText size={18} className="text-text-muted" />
              )}
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-text truncate">{doc.name}</h3>
              <p className="text-[11px] text-text-muted">
                {typeLabels[doc.type] || typeLabels.other}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-black/5 text-text-muted transition-colors cursor-pointer flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>
        {viewTabs.length > 1 && (
          <Tabs
            tabs={viewTabs}
            activeTab={mode}
            onChange={(id) => onModeChange(id as PreviewMode)}
          />
        )}
      </div>

      {mode === "file" && canPreviewFile ? (
        <iframe
          src={doc.blobUrl}
          title={doc.name}
          className="flex-1 w-full border-0 bg-white"
        />
      ) : mode === "content" && content ? (
        <div className="flex-1 overflow-y-auto">
          {content.metadata.title && (
            <div className="px-5 pt-5 pb-3">
              <h2 className="text-base font-bold text-text">{content.metadata.title}</h2>
              {content.metadata.author && (
                <p className="text-xs text-text-muted mt-1">{content.metadata.author}</p>
              )}
              {content.metadata.siteName && (
                <p className="text-xs text-accent-blue mt-0.5">{content.metadata.siteName}</p>
              )}
            </div>
          )}
          <div className="px-5 pb-5">
            <div className="prose prose-sm max-w-none dark:prose-invert
              prose-pre:bg-gray-100 prose-pre:rounded-xl prose-pre:border prose-pre:border-border
              prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
              dark:prose-pre:bg-gray-800/50 dark:prose-code:bg-gray-800/50
            ">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content.markdown}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-5">
          <div className="flex flex-col gap-5">
            <div className="flex items-center gap-2">
              <Badge variant={doc.status === "ready" ? "success" : doc.status === "error" ? "danger" : "warning"}>
                {doc.status === "ready" ? "Готов" : doc.status === "error" ? "Ошибка" : "Обработка"}
              </Badge>
              {doc.type !== "url" && <Badge variant="accent">{doc.type.toUpperCase()}</Badge>}
            </div>

            {doc.status === "error" && doc.errorMessage && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-600">
                {doc.errorMessage}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {doc.size != null && (
                <div className="flex items-center gap-2 p-3 rounded-xl glass">
                  <HardDrive size={14} className="text-text-muted" />
                  <div>
                    <p className="text-[10px] text-text-muted uppercase tracking-wider">Размер</p>
                    <p className="text-xs font-medium text-text">{formatSize(doc.size)}</p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2 p-3 rounded-xl glass">
                <Clock size={14} className="text-text-muted" />
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Загружен</p>
                  <p className="text-xs font-medium text-text">{formatDate(doc.uploadedAt)}</p>
                </div>
              </div>
            </div>

            {isUrl ? (
              <div className="flex flex-col gap-3 p-4 rounded-2xl bg-accent-blue-bg/50 border border-accent-blue-border/20">
                <p className="text-xs font-medium text-accent-blue">
                  {hasExtractedContent
                    ? "Содержимое извлечено. Перейдите на вкладку «Контент» для просмотра."
                    : "Ссылка на внешний источник. Содержимое скачивается и обрабатывается."}
                </p>
                {hasRealUrl && (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs text-accent-blue hover:underline break-all"
                  >
                    <ExternalLink size={12} />
                    {doc.url}
                  </a>
                )}
              </div>
            ) : doc.status === "ready" ? (
              <AttentionView
                icon={<FileText size={32} />}
                title="Файл сохранён в системе"
                description={
                  canPreviewFile
                    ? "Документ готов к использованию. Нажмите «Файл» для просмотра содержимого."
                    : "Документ загружен и готов к использованию в генерации гипотез."
                }
                variant="green"
                size="md"
                blur
                className="py-4"
              />
            ) : doc.status === "processing" ? (
              <ProcessingState />
            ) : doc.status === "error" ? (
              <AttentionView
                icon={<X size={32} />}
                title="Ошибка загрузки"
                description={doc.errorMessage || "Не удалось загрузить документ. Попробуйте ещё раз."}
                variant="amber"
                size="md"
                className="py-4"
              />
            ) : null}

            <div className="border-t border-border pt-4">
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                Информация о файле
              </h4>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
                <dt className="text-[11px] text-text-muted">Тип</dt>
                <dd className="text-[11px] text-text">{typeLabels[doc.type] || typeLabels.other}</dd>
                <dt className="text-[11px] text-text-muted">Формат</dt>
                <dd className="text-[11px] text-text">{doc.type.toUpperCase()}</dd>
                <dt className="text-[11px] text-text-muted">Статус</dt>
                <dd className="text-[11px] text-text">
                  {doc.status === "ready" ? "Готов к использованию" : doc.status === "processing" ? "Идёт обработка..." : "Ошибка загрузки"}
                </dd>
                <dt className="text-[11px] text-text-muted">Источник</dt>
                <dd className="text-[11px] text-text">
                  {isUrl ? "Внешняя ссылка" : "Локальная загрузка"}
                </dd>
                {hasRealUrl && (
                  <>
                    <dt className="text-[11px] text-text-muted">Ссылка</dt>
                    <dd className="text-[11px] text-accent-blue truncate">
                      <a href={doc.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                        {doc.url}
                      </a>
                    </dd>
                  </>
                )}
                {content?.metadata.language && (
                  <>
                    <dt className="text-[11px] text-text-muted">Язык</dt>
                    <dd className="text-[11px] text-text">{content.metadata.language.toUpperCase()}</dd>
                  </>
                )}
                {content?.statusCode != null && (
                  <>
                    <dt className="text-[11px] text-text-muted">HTTP статус</dt>
                    <dd className="text-[11px] text-text">{content.statusCode}</dd>
                  </>
                )}
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
