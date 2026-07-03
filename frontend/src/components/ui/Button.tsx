import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success" | "info" | "warning";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent/90 backdrop-blur-sm text-white hover:bg-accent active:scale-[0.98] shadow-button hover:shadow-button-hover border border-accent-border/30",
  secondary:
    "glass text-text hover:bg-white/90 active:scale-[0.98] shadow-button hover:shadow-button-hover",
  ghost:
    "text-text-muted hover:bg-black/5 active:scale-[0.98]",
  danger:
    "bg-red-500/90 backdrop-blur-sm text-white hover:bg-red-600 active:scale-[0.98] shadow-button hover:shadow-button-hover border border-red-400/20",
  success:
    "bg-accent-green/90 backdrop-blur-sm text-white hover:bg-accent-green-hover active:scale-[0.98] shadow-button hover:shadow-button-hover border border-accent-green-border/30",
  info:
    "bg-accent-blue/90 backdrop-blur-sm text-white hover:bg-accent-blue-hover active:scale-[0.98] shadow-button hover:shadow-button-hover border border-accent-blue-border/30",
  warning:
    "bg-accent-amber/90 backdrop-blur-sm text-white hover:bg-accent-amber-hover active:scale-[0.98] shadow-button hover:shadow-button-hover border border-accent-amber-border/30",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs gap-1.5 rounded-lg",
  md: "px-4 py-2.5 text-sm gap-2 rounded-xl",
  lg: "px-6 py-3 text-base gap-2.5 rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", loading, icon, children, className = "", disabled, ...props },
    ref,
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-all duration-200 cursor-pointer
        disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100
        ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        <span className="flex-shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  ),
);

Button.displayName = "Button";
