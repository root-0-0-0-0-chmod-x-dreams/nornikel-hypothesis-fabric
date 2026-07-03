interface ProgressProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: "sm" | "md" | "lg";
  color?: "accent" | "blue" | "green" | "amber";
  className?: string;
}

const heightStyles = { sm: "h-1.5", md: "h-2", lg: "h-3" };

const colorStyles = {
  accent: "bg-accent",
  blue: "bg-accent-blue",
  green: "bg-accent-green",
  amber: "bg-accent-amber",
};

export function Progress({ value, max = 100, label, showValue = false, size = "md", color = "accent", className = "" }: ProgressProps) {
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
          className={`${heightStyles[size]} rounded-full transition-all duration-500 ease-out ${colorStyles[color]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
