interface ProgressProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const heightStyles = { sm: "h-1", md: "h-2", lg: "h-3" };

export function Progress({ value, max = 100, label, showValue = false, size = "md", className = "" }: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {(label || showValue) && (
        <div className="flex items-center justify-between">
          {label && <span className="text-xs font-medium text-text-muted">{label}</span>}
          {showValue && <span className="text-xs font-medium text-text-muted">{Math.round(pct)}%</span>}
        </div>
      )}
      <div className={`w-full bg-gray-100 rounded-full overflow-hidden ${heightStyles[size]}`}>
        <div
          className={`${heightStyles[size]} bg-accent rounded-full transition-all duration-500 ease-out
            ${pct < 100 ? "bg-gradient-to-r from-accent via-accent to-violet-400 animate-shimmer" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
