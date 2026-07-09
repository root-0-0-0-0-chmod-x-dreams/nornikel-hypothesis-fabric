import { Check, Play, X, Clock, FileText, type LucideIcon } from "lucide-react";
import type { RoadmapStep } from "@/types";

interface RoadmapTimelineProps {
  steps: RoadmapStep[];
  className?: string;
}

const statusConfig: Record<RoadmapStep["status"], { icon: LucideIcon; color: string; lineColor: string }> = {
  pending: { icon: Clock, color: "text-text-muted border-border bg-white", lineColor: "bg-gray-200" },
  in_progress: { icon: Play, color: "text-accent border-accent/50 bg-accent-bg", lineColor: "bg-accent/40" },
  completed: { icon: Check, color: "text-accent-green border-accent-green/50 bg-accent-green-bg", lineColor: "bg-accent-green/40" },
  failed: { icon: X, color: "text-red-500 border-red-400/50 bg-red-50", lineColor: "bg-red-400/40" },
};

export function RoadmapTimeline({ steps, className = "" }: RoadmapTimelineProps) {
  const sorted = [...steps].sort((a, b) => a.order - b.order);

  return (
    <div className={`flex flex-col ${className}`}>
      {sorted.map((step, i) => {
        const cfg = statusConfig[step.status];
        const Icon = cfg.icon;
        const isLast = i === sorted.length - 1;

        return (
          <div key={step.id} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 shadow-sm ${cfg.color}`}>
                <Icon size={14} />
              </div>
              {!isLast && (
                <div className={`w-0.5 flex-1 min-h-6 mt-2 rounded-full ${cfg.lineColor}`} />
              )}
            </div>
            <div className="pb-6">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-text-muted">Шаг {step.order}</span>
                <span className="text-xs text-text-muted/60">{step.duration}</span>
              </div>
              <h4 className="text-sm font-semibold text-text mt-0.5">{step.title}</h4>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">{step.description}</p>
              <div className="flex flex-wrap gap-3 mt-2">
                <span className="text-[11px] text-text-muted">
                  Ресурсы: {step.resources}
                </span>
              </div>
              {step.successCriteria && step.successCriteria !== "—" && (
                <p className="text-[11px] text-accent-green mt-2">
                  Успех: {step.successCriteria}
                </p>
              )}
              {step.sourceDetails && step.sourceDetails.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted flex items-center gap-1">
                    <FileText size={11} />
                    Параграфы
                  </p>
                  {step.sourceDetails.map((src, si) => (
                    <a
                      key={`${src.chunkId ?? src.title}-${si}`}
                      href={src.url ?? (src.chunkId ? `/api/v1/sources/chunks/${src.chunkId}` : undefined)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-xs text-accent hover:underline leading-snug"
                    >
                      {src.title}
                      {src.page != null && ` · стр. ${src.page}`}
                      {src.paragraphIndex != null && ` · §${src.paragraphIndex + 1}`}
                    </a>
                  ))}
                </div>
              )}
              {step.status === "failed" && step.failureCriteria && (
                <div className="mt-2 px-3 py-2 bg-red-50 rounded-xl text-xs text-red-600">
                  Причина: {step.failureCriteria}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
