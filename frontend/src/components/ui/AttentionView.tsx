import { type ReactNode } from "react";

export type AttentionVariant = "accent" | "blue" | "green" | "amber" | "gray";
export type AttentionSize = "sm" | "md" | "lg";

interface AttentionViewProps {
  icon: ReactNode;
  title: string;
  description?: string;
  variant?: AttentionVariant;
  size?: AttentionSize;
  blur?: boolean;
  gradient?: boolean;
  className?: string;
}

const variantMap: Record<AttentionVariant, {
  bg: string;
  text: string;
  blurBg: string;
  ring: string;
  gradient: string;
}> = {
  accent: {
    bg: "bg-accent-bg",
    text: "text-accent",
    blurBg: "bg-accent/15",
    ring: "ring-accent/20",
    gradient: "linear-gradient(135deg, oklch(0.55 0.22 280 / 0.18), oklch(0.62 0.18 300 / 0.06), oklch(0.5 0.22 270 / 0.04))",
  },
  blue: {
    bg: "bg-accent-blue-bg",
    text: "text-accent-blue",
    blurBg: "bg-accent-blue/15",
    ring: "ring-accent-blue/20",
    gradient: "linear-gradient(135deg, oklch(0.55 0.18 250 / 0.18), oklch(0.6 0.14 230 / 0.06), oklch(0.5 0.2 260 / 0.04))",
  },
  green: {
    bg: "bg-accent-green-bg",
    text: "text-accent-green",
    blurBg: "bg-accent-green/15",
    ring: "ring-accent-green/20",
    gradient: "linear-gradient(135deg, oklch(0.55 0.18 160 / 0.18), oklch(0.6 0.14 150 / 0.06), oklch(0.5 0.2 170 / 0.04))",
  },
  amber: {
    bg: "bg-accent-amber-bg",
    text: "text-accent-amber",
    blurBg: "bg-accent-amber/15",
    ring: "ring-accent-amber/20",
    gradient: "linear-gradient(135deg, oklch(0.65 0.16 85 / 0.18), oklch(0.7 0.14 75 / 0.06), oklch(0.6 0.18 90 / 0.04))",
  },
  gray: {
    bg: "bg-gray-100",
    text: "text-text-muted",
    blurBg: "bg-gray-200/50",
    ring: "ring-gray-200/50",
    gradient: "linear-gradient(135deg, oklch(0.6 0 0 / 0.12), oklch(0.7 0 0 / 0.06), oklch(0.55 0 0 / 0.04))",
  },
};

const iconSizes: Record<AttentionSize, { container: string; iconClass: string }> = {
  sm: { container: "p-2.5 rounded-xl", iconClass: "[&>svg]:w-5 [&>svg]:h-5" },
  md: { container: "p-4 rounded-2xl", iconClass: "[&>svg]:w-8 [&>svg]:h-8" },
  lg: { container: "p-5 rounded-2xl", iconClass: "[&>svg]:w-10 [&>svg]:h-10" },
};

const blurSizes: Record<AttentionSize, string> = {
  sm: "w-16 h-16 -top-3 -left-3",
  md: "w-28 h-28 -top-6 -left-6",
  lg: "w-36 h-36 -top-8 -left-8",
};

const titleSizes: Record<AttentionSize, string> = {
  sm: "text-xs font-semibold",
  md: "text-sm font-semibold",
  lg: "text-lg font-bold",
};

const descSizes: Record<AttentionSize, string> = {
  sm: "text-[11px]",
  md: "text-xs",
  lg: "text-sm",
};

export function AttentionView({
  icon,
  title,
  description,
  variant = "gray",
  size = "md",
  blur = false,
  gradient = false,
  className = "",
}: AttentionViewProps) {
  const c = variantMap[variant];
  const s = iconSizes[size];

  return (
    <div className={`flex flex-col items-center gap-4 text-center ${className}`}>
      <div className="relative">
        {blur && (
          <div
            className={`absolute rounded-full blur-2xl opacity-60 ${blurSizes[size]} ${c.blurBg}`}
          />
        )}
        <div
          className={`relative flex items-center justify-center ${s.container} ${gradient ? "" : c.bg} ${blur ? "ring-1 " + c.ring : ""}`}
          style={gradient ? { background: c.gradient } : undefined}
        >
          <div className={`${c.text} ${s.iconClass}`}>
            {icon}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-1 max-w-xs">
        <p className={`${titleSizes[size]} text-text`}>{title}</p>
        {description && (
          <p className={`${descSizes[size]} text-text-muted leading-relaxed`}>
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
