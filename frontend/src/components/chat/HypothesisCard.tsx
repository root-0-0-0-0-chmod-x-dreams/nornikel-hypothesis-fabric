import { useState } from "react";
import { Badge, Card } from "@/components/ui";
import type { BadgeVariant } from "@/components/ui/Badge";
import { ChevronDown, ChevronRight, Lightbulb, AlertTriangle, TrendingUp, BookOpen, FlaskConical, Target, Link, BarChart3 } from "lucide-react";
import type { Hypothesis } from "@/types";

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  onSourceClick?: (source: string) => void;
}

const noveltyColors: Record<Hypothesis["novelty"], BadgeVariant> = {
  high: "success",
  medium: "warning",
  low: "default",
};

const noveltyLabels: Record<Hypothesis["novelty"], string> = {
  high: "Высокая новизна",
  medium: "Средняя новизна",
  low: "Низкая новизна",
};

export function HypothesisCard({ hypothesis: h, onSourceClick }: HypothesisCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card padding="lg" className="animate-slide-up">
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-accent-bg flex-shrink-0 mt-0.5">
            <Lightbulb size={18} className="text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-text leading-relaxed">{h.title}</h3>
            <p className="text-xs text-text-muted mt-1.5 leading-relaxed">{h.description}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant={noveltyColors[h.novelty]}>{noveltyLabels[h.novelty]}</Badge>
          {h.confidence != null && (
            <Badge variant="info">{Math.round(h.confidence * 100)}% уверенность</Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-50/50">
            <AlertTriangle size={14} className="text-accent-amber mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Технические риски</p>
              <p className="text-xs text-text">{h.risks.technical}</p>
            </div>
          </div>
          <div className="flex items-start gap-2 p-2.5 rounded-xl bg-accent-green-bg/50">
            <TrendingUp size={14} className="text-accent-green mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Экономические риски</p>
              <p className="text-xs text-text">{h.risks.economic}</p>
            </div>
          </div>
        </div>

        {h.confidence != null && (
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-text-muted uppercase tracking-wider">Уверенность модели</span>
              <span className="text-[10px] font-semibold text-accent">{Math.round(h.confidence * 100)}%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full bg-accent transition-all duration-500"
                style={{ width: `${Math.round(h.confidence * 100)}%` }}
              />
            </div>
          </div>
        )}

        <div className="p-3 rounded-xl glass">
          <div className="flex items-center gap-1.5 mb-1">
            <Target size={12} className="text-accent" />
            <p className="text-xs font-semibold text-accent">Ожидаемая ценность</p>
          </div>
          <p className="text-xs text-text leading-relaxed">{h.expectedValue}</p>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs text-accent hover:underline cursor-pointer"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {expanded ? "Скрыть детали" : "Научное обоснование и источники"}
        </button>

        {expanded && (
          <div className="flex flex-col gap-4 pt-3 border-t border-border animate-fade-in">
            <div className="flex items-start gap-2">
              <FlaskConical size={14} className="text-accent mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Механизм влияния</p>
                <p className="text-xs text-text leading-relaxed">{h.mechanism}</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <BookOpen size={14} className="text-accent-blue mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Научное обоснование</p>
                <p className="text-xs text-text leading-relaxed">{h.rationale}</p>
              </div>
            </div>

            {h.noveltyRationale && (
              <div className="flex items-start gap-2">
                <BarChart3 size={14} className="text-accent-green mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Обоснование новизны</p>
                  <p className="text-xs text-text leading-relaxed">{h.noveltyRationale}</p>
                </div>
              </div>
            )}

            {h.sources.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Link size={12} className="text-accent-blue" />
                  <p className="text-[10px] text-text-muted uppercase tracking-wider">Источники</p>
                </div>
                <div className="flex flex-col gap-1.5">
                  {h.sources.map((src, i) => (
                    <button
                      key={i}
                      onClick={() => onSourceClick?.(src)}
                      className="flex gap-2 p-2 rounded-lg bg-accent-blue-bg/50 hover:bg-accent-blue-bg text-left cursor-pointer transition-colors w-full"
                    >
                      <span className="text-[10px] font-semibold text-accent-blue font-mono flex-shrink-0">[{i + 1}]</span>
                      <p className="text-xs text-text leading-relaxed hover:text-accent-blue transition-colors">{src}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
