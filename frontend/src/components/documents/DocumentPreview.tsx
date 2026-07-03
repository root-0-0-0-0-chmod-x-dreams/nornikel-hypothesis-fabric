import { X, FileText, Globe, ExternalLink, Clock, HardDrive, Info, Eye } from "lucide-react";
import { Badge, Tabs } from "@/components/ui";
import type { Document } from "@/types";

interface DocumentPreviewProps {
  document: Document;
  mode: "info" | "file";
  onModeChange: (mode: "info" | "file") => void;
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

export function DocumentPreview({ document: doc, mode, onModeChange, onClose }: DocumentPreviewProps) {
  const isUrl = doc.type === "url";
  const hasRealUrl = isRealUrl(doc.url);
  const canPreviewFile = doc.blobUrl && previewableBlobTypes.includes(doc.type);

  const viewTabs = [
    { id: "info", label: "Инфо", icon: <Info size={14} /> },
    ...(canPreviewFile ? [{ id: "file" as const, label: "Файл", icon: <Eye size={14} /> }] : []),
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`p-2 rounded-lg ${isUrl ? "bg-blue-50" : "bg-gray-100"} flex-shrink-0`}>
              {isUrl ? (
                <Globe size={18} className="text-blue-600" />
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
            className="p-2 rounded-lg hover:bg-gray-100 text-text-muted transition-colors cursor-pointer flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>
        {viewTabs.length > 1 && (
          <Tabs
            tabs={viewTabs}
            activeTab={mode}
            onChange={(id) => onModeChange(id as "info" | "file")}
          />
        )}
      </div>

      {mode === "file" && canPreviewFile ? (
        <iframe
          src={doc.blobUrl}
          title={doc.name}
          className="flex-1 w-full border-0"
        />
      ) : (
        <div className="flex-1 overflow-y-auto p-5">
          <div className="flex flex-col gap-5">
            <div className="flex items-center gap-2">
              <Badge variant={doc.status === "ready" ? "success" : doc.status === "error" ? "danger" : "warning"}>
                {doc.status === "ready" ? "Готов" : doc.status === "error" ? "Ошибка" : "Обработка"}
              </Badge>
              {doc.type !== "url" && <Badge variant="accent">{doc.type.toUpperCase()}</Badge>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              {doc.size != null && (
                <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                  <HardDrive size={14} className="text-text-muted" />
                  <div>
                    <p className="text-[10px] text-text-muted uppercase tracking-wider">Размер</p>
                    <p className="text-xs font-medium text-text">{formatSize(doc.size)}</p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                <Clock size={14} className="text-text-muted" />
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Загружен</p>
                  <p className="text-xs font-medium text-text">{formatDate(doc.uploadedAt)}</p>
                </div>
              </div>
            </div>

            {isUrl ? (
              <div className="flex flex-col gap-3 p-4 bg-blue-50 rounded-xl border border-blue-100">
                <p className="text-xs font-medium text-blue-800">
                  Ссылка на внешний источник. Содержимое скачивается и обрабатывается для индексации.
                </p>
                {hasRealUrl && (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline break-all"
                  >
                    <ExternalLink size={12} />
                    {doc.url}
                  </a>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center gap-4 py-8 text-center">
                <div className="p-4 rounded-2xl bg-gray-100">
                  <FileText size={32} className="text-text-muted/40" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text">Файл сохранён в системе</p>
                  <p className="text-xs text-text-muted mt-1 max-w-xs">
                    Документ загружен и готов к использованию в генерации гипотез.
                    {canPreviewFile && " Нажмите «Файл» для просмотра содержимого."}
                  </p>
                </div>
              </div>
            )}

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
                    <dd className="text-[11px] text-accent truncate">
                      <a href={doc.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                        {doc.url}
                      </a>
                    </dd>
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
