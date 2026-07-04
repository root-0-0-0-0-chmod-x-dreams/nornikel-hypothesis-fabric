import { Card } from "@/components/ui";
import { RoadmapTimeline } from "./RoadmapTimeline";
import type { Roadmap } from "@/types";
import { Clock, Wrench } from "lucide-react";

interface RoadmapViewProps {
  roadmap: Roadmap;
  className?: string;
}

export function RoadmapView({ roadmap, className = "" }: RoadmapViewProps) {
  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      <div className="flex items-center gap-3">
        <div>
          <h3 className="text-sm font-semibold text-text">Дорожная карта проверки</h3>
          <p className="text-xs text-text-muted mt-0.5">Гипотеза: {roadmap.hypothesisId}</p>
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Clock size={12} />
          {roadmap.totalDuration}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Wrench size={12} />
          {roadmap.totalResources}
        </div>
      </div>

      <Card padding="lg">
        <RoadmapTimeline steps={roadmap.steps} />
      </Card>
    </div>
  );
}
