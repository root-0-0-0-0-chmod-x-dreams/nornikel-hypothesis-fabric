type BadgeVariant = "default" | "success" | "warning" | "danger" | "accent" | "info";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-600",
  success: "bg-accent-green-bg text-accent-green",
  warning: "bg-accent-amber-bg text-accent-amber",
  danger: "bg-red-50 text-red-600",
  accent: "bg-accent-bg text-accent",
  info: "bg-accent-blue-bg text-accent-blue",
};

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium
      ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
