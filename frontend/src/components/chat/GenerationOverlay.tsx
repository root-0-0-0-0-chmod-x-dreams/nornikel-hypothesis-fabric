import { Spinner, Badge } from "@/components/ui";
import type { AgentNodeData } from "./AgentNode";
import { AgentNode } from "./AgentNode";

interface GenerationOverlayProps {
  phase: "retrieve" | "generate" | "validate" | "done";
  nodes: AgentNodeData[];
  progress: number;
  hypothesisCount: number;
  cycleDepth: number;
}

const phaseLabels: Record<GenerationOverlayProps["phase"], { label: string; color: string }> = {
  retrieve: { label: "Поиск релевантных документов", color: "text-accent-blue" },
  generate: { label: "Генерация гипотез", color: "text-accent" },
  validate: { label: "Проверка и критика", color: "text-accent-amber" },
  done: { label: "Завершено", color: "text-accent-green" },
};

export function GenerationOverlay({ phase, nodes, progress, hypothesisCount, cycleDepth }: GenerationOverlayProps) {
  const phaseInfo = phaseLabels[phase];

  return (
    <div className="px-4 pt-3 pb-1 border-b border-border/50 bg-surface-alt/30 animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex items-center gap-2">
          {phase !== "done" && <Spinner size={14} className={phaseInfo.color} />}
          <span className={`text-xs font-semibold ${phaseInfo.color}`}>
            {phaseInfo.label}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <Badge variant="accent">{hypothesisCount} гипотез</Badge>
          <Badge variant="default">цикл {cycleDepth}</Badge>
        </div>
      </div>

      {nodes.length > 0 && (
        <div className="flex flex-col gap-2 mb-2">
          {nodes.map((node) => (
            <AgentNode key={node.id} node={node} />
          ))}
        </div>
      )}

      {phase !== "done" && (
        <div className="w-full bg-gray-100 rounded-full h-1 mb-1">
          <div
            className="h-1 rounded-full bg-accent transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
