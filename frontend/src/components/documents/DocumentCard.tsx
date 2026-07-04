import { useState, useEffect, useRef } from "react";
import { FileText, FileSpreadsheet, Globe, Image, X, Loader, ExternalLink, Eye } from "lucide-react";
import { Card, Badge, Progress } from "@/components/ui";
import type { Document } from "@/types";

interface DocumentCardProps {
  document: Document;
  onRemove?: (id: string) => void;
  onClick?: (doc: Document) => void;
  onPreview?: (doc: Document) => void;
}

const iconMap = {
  pdf: FileText,
  docx: FileText,
  xlsx: FileSpreadsheet,
  url: Globe,
  image: Image,
  other: FileText,
};

const statusMap: Record<Document["status"], { label: string; variant: "default" | "success" | "warning" | "danger" | "accent" | "info" }> = {
  uploading: { label: "Загружается", variant: "warning" },
  processing: { label: "Обработка", variant: "warning" },
  ready: { label: "Готов", variant: "success" },
  error: { label: "Ошибка", variant: "danger" },
};

function formatSize(bytes?: number): string {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

function hasRealUrl(url: string): boolean {
  return url.length > 0 && url !== "#" && (url.startsWith("http://") || url.startsWith("https://"));
}

export function DocumentCard({ document: doc, onRemove, onClick, onPreview }: DocumentCardProps) {
  const Icon = iconMap[doc.type] || FileText;
  const isProcessing = doc.status === "uploading" || doc.status === "processing";
  const isUrl = doc.type === "url";
  const showExternalLink = hasRealUrl(doc.url);
  const canPreview = !!doc.blobUrl;

  const [progress, setProgress] = useState(0);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isProcessing) {
      const startedAt = Date.now();
      const duration = 15_000;
      progressRef.current = setInterval(() => {
        const elapsed = Date.now() - startedAt;
        setProgress(Math.min(92, Math.round((elapsed / duration) * 92)));
      }, 200);
    } else {
      setProgress(0);
    }
    return () => {
      if (progressRef.current) clearInterval(progressRef.current);
    };
  }, [isProcessing, doc.id]);

  return (
    <Card padding="sm" hover={!!onClick && !isProcessing} onClick={onClick ? () => onClick(doc) : undefined}>
      <div className="flex flex-col gap-2">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-xl ${isProcessing ? "bg-accent-amber-bg" : isUrl ? "bg-accent-blue-bg" : "bg-gray-100"} flex-shrink-0`}>
            {isProcessing ? (
              <Loader size={16} className="text-accent-amber animate-spin" />
            ) : (
              <Icon size={16} className={isUrl ? "text-accent-blue" : "text-text-muted"} />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <p className="text-sm font-medium text-text truncate">{doc.name}</p>
              {isUrl && <Globe size={11} className="text-accent-blue flex-shrink-0" />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={statusMap[doc.status].variant}>
                {statusMap[doc.status].label}
              </Badge>
              {doc.size && <span className="text-[11px] text-text-muted">{formatSize(doc.size)}</span>}
              {isUrl && <span className="text-[11px] text-accent-blue">ссылка</span>}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {canPreview && onPreview && doc.status === "ready" && (
              <button
                onClick={(e) => { e.stopPropagation(); onPreview(doc); }}
                className="p-1.5 rounded-xl hover:bg-accent-bg text-text-muted hover:text-accent transition-colors cursor-pointer"
                title="Посмотреть файл"
              >
                <Eye size={14} />
              </button>
            )}
            {showExternalLink && (
              <a
                href={doc.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-1.5 rounded-xl hover:bg-accent-blue-bg text-text-muted hover:text-accent-blue transition-colors"
                title="Открыть источник"
              >
                <ExternalLink size={14} />
              </a>
            )}
            {onRemove && (
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(doc.id); }}
                className="p-1.5 rounded-xl hover:bg-red-50 text-text-muted hover:text-red-500 transition-colors cursor-pointer"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>
        {isProcessing && progress > 0 && (
          <Progress value={progress} size="sm" color="amber" showValue />
        )}
      </div>
    </Card>
  );
}
