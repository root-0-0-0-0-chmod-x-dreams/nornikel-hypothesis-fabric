import type { Hypothesis } from "@/types";
import { HypothesisCard } from "./HypothesisCard";

interface HypothesisListProps {
  hypotheses: Hypothesis[];
  selectedId?: string;
  onSelect?: (hypothesis: Hypothesis) => void;
}

export function HypothesisList({ hypotheses, selectedId, onSelect }: HypothesisListProps) {
  if (!hypotheses.length) return null;

  return (
    <div className="flex flex-col gap-4 w-full">
      {hypotheses.map((h) => (
        <HypothesisCard
          key={h.id}
          hypothesis={h}
          selected={h.id === selectedId}
          onSelect={onSelect ? () => onSelect(h) : undefined}
        />
      ))}
    </div>
  );
}
