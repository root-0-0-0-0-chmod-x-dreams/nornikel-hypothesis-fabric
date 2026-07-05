import { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Search, ShieldCheck } from "lucide-react";

export interface AgentNodeData {
  id: string;
  agent: "generator" | "actor" | "judge";
  title: string;
  summary: string;
  detail: string;
  timestamp: number;
}

interface AgentNodeProps {
  node: AgentNodeData;
}

const agentConfig = {
  generator: {
    icon: Brain,
    label: "Generator",
    color: "bg-accent-bg text-accent border-accent-border/30",
    iconColor: "text-accent",
  },
  actor: {
    icon: Search,
    label: "Actor",
    color: "bg-accent-blue-bg text-accent-blue border-accent-blue-border/30",
    iconColor: "text-accent-blue",
  },
  judge: {
    icon: ShieldCheck,
    label: "Judge",
    color: "bg-accent-amber-bg text-accent-amber border-accent-amber-border/30",
    iconColor: "text-accent-amber",
  },
};

export function AgentNode({ node }: AgentNodeProps) {
  const [expanded, setExpanded] = useState(false);
  const cfg = agentConfig[node.agent];
  const Icon = cfg.icon;

  return (
    <div className={`rounded-xl border ${cfg.color} p-3 animate-fade-in`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 w-full text-left cursor-pointer"
      >
        <div className={`p-1.5 rounded-lg ${cfg.color}`}>
          <Icon size={14} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold">{cfg.label}</span>
            <span className="text-[10px] text-text-muted">
              {node.timestamp.toFixed(1)}s
            </span>
          </div>
          <p className="text-xs text-text-muted truncate mt-0.5">{node.summary}</p>
        </div>
        {expanded ? <ChevronDown size={14} className="text-text-muted flex-shrink-0" /> : <ChevronRight size={14} className="text-text-muted flex-shrink-0" />}
      </button>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/50">
          <p className="text-xs text-text leading-relaxed whitespace-pre-wrap">{node.detail}</p>
        </div>
      )}
    </div>
  );
}
