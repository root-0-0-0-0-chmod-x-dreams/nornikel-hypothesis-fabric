import { Check, Play, X, Clock, type LucideIcon } from "lucide-react";
import type { RoadmapStep } from "@/types";

interface RoadmapTimelineProps {
  steps: RoadmapStep[];
  className?: string;
}

const statusConfig: Record<RoadmapStep["status"], { icon: LucideIcon; color: string; lineColor: string }> = {
  pending: { icon: Clock, color: "text-text-muted border-border bg-white", lineColor: "bg-gray-200" },
  in_progress: { icon: Play, color: "text-accent border-accent bg-accent-bg", lineColor: "bg-accent" },
  completed: { icon: Check, color: "text-emerald-600 border-emerald-500 bg-emerald-50", lineColor: "bg-emerald-500" },
  failed: { icon: X, color: "text-red-600 border-red-500 bg-red-50", lineColor: "bg-red-500" },
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
              <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${cfg.color}`}>
                <Icon size={14} />
              </div>
              {!isLast && (
                <div className={`w-0.5 flex-1 min-h-6 mt-2 ${cfg.lineColor}`} />
              )}
            </div>
            <div className={`pb-6 ${isLast ? "" : ""}`}>
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
              {step.status === "failed" && step.failureCriteria && (
                <div className="mt-2 px-3 py-2 bg-red-50 rounded-lg text-xs text-red-700">
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
