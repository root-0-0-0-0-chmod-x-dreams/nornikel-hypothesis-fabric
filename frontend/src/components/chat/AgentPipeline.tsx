import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Clock, Cpu, Scale, Sparkles } from "lucide-react";
import type { AgentStep } from "@/types";
import { Badge, Card } from "@/components/ui";

interface AgentPipelineProps {
  steps: AgentStep[];
  hypothesisCount?: number;
  cycleDepth?: number;
  isRunning?: boolean;
  elapsedSeconds?: number;
}

function formatElapsed(seconds?: number): string {
  const total = Math.max(0, Math.floor(seconds ?? 0));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

const agentConfig = {
  generator: { label: "Generator", icon: Sparkles, color: "text-accent bg-accent-bg" },
  actor: { label: "Actor", icon: Cpu, color: "text-accent-blue bg-accent-blue-bg" },
  judge: { label: "Judge", icon: Scale, color: "text-accent-green bg-accent-green-bg" },
};

function AgentStepRow({
  step,
  defaultOpen,
  liveElapsed,
}: {
  step: AgentStep;
  defaultOpen?: boolean;
  liveElapsed?: number;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const cfg = agentConfig[step.agent];
  const Icon = cfg.icon;
  const isRunning = step.status === "running";
  const displayTimestamp = isRunning && liveElapsed != null ? liveElapsed : step.timestamp;

  return (
    <div className={`rounded-xl border ${isRunning ? "border-accent-border bg-accent-bg/30" : "border-border bg-white/60"}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start gap-3 p-3 text-left cursor-pointer"
      >
        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${cfg.color}`}>
          <Icon size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">{cfg.label}</span>
            <span className="text-[10px] text-text-muted">{displayTimestamp.toFixed(1)}s</span>
            {isRunning && <Badge variant="accent">в процессе</Badge>}
          </div>
          <p className="text-sm font-medium text-text mt-0.5">{step.title}</p>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">{step.summary}</p>
        </div>
        {open ? <ChevronDown size={16} className="text-text-muted mt-1" /> : <ChevronRight size={16} className="text-text-muted mt-1" />}
      </button>
      {open && step.detail && (
        <div className="px-3 pb-3 pl-14">
          <p className="text-xs text-text leading-relaxed whitespace-pre-wrap">{step.detail}</p>
        </div>
      )}
    </div>
  );
}

export function AgentPipeline({ steps, hypothesisCount, cycleDepth, isRunning, elapsedSeconds }: AgentPipelineProps) {
  const [displayElapsed, setDisplayElapsed] = useState(elapsedSeconds ?? 0);

  useEffect(() => {
    setDisplayElapsed(elapsedSeconds ?? 0);
  }, [elapsedSeconds]);

  if (!steps.length) return null;

  return (
    <Card padding="md" className="w-full">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h4 className="text-sm font-semibold text-text">Генерация гипотез</h4>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <Badge variant="default">
            <span className="inline-flex items-center gap-1">
              <Clock size={11} />
              {formatElapsed(displayElapsed)}
            </span>
          </Badge>
          {hypothesisCount != null && (
            <Badge variant="accent">{hypothesisCount} гипотез</Badge>
          )}
          {cycleDepth != null && (
            <Badge variant="info">цикл {cycleDepth}</Badge>
          )}
          {isRunning && <Badge variant="warning">Agent-Judge</Badge>}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        {steps.map((step, i) => (
          <AgentStepRow
            key={step.id}
            step={step}
            liveElapsed={elapsedSeconds}
            defaultOpen={i === steps.length - 1}
          />
        ))}
      </div>
    </Card>
  );
}
