import { Card } from "@/components/ui";
import { RoadmapTimeline } from "./RoadmapTimeline";
import { ParagraphList } from "@/components/documents/ParagraphList";
import type { Roadmap } from "@/types";
import { Clock, Wrench, BookOpen } from "lucide-react";

interface RoadmapViewProps {
  roadmap: Roadmap;
  hypothesisTitle?: string;
  className?: string;
}

export function RoadmapView({ roadmap, hypothesisTitle, className = "" }: RoadmapViewProps) {
  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      <div className="flex items-center gap-3">
        <div>
          <h3 className="text-lg font-semibold text-text">Дорожная карта проверки</h3>
          <p className="text-sm text-text-muted mt-1 leading-relaxed">
            {hypothesisTitle ?? roadmap.hypothesisId}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-1.5 text-sm text-text-muted">
          <Clock size={14} />
          {roadmap.totalDuration}
        </div>
        <div className="flex items-center gap-1.5 text-sm text-text-muted">
          <Wrench size={14} />
          {roadmap.totalResources}
        </div>
      </div>

      {roadmap.sourceDetails && roadmap.sourceDetails.length > 0 && (
        <Card padding="md">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={16} className="text-accent" />
            <h4 className="text-sm font-semibold text-text">Источники и параграфы</h4>
          </div>
          <ParagraphList paragraphs={roadmap.sourceDetails} />
        </Card>
      )}

      <Card padding="lg">
        <RoadmapTimeline steps={roadmap.steps} />
      </Card>
    </div>
  );
}
