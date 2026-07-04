import { type ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
  glass?: boolean;
}

const paddingStyles = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export function Card({ children, className = "", onClick, hover = false, padding = "md", glass = true }: CardProps) {
  const Component = onClick ? "button" : "div";
  return (
    <Component
      onClick={onClick}
      className={`rounded-2xl border border-border shadow-card
        ${glass ? "glass" : "bg-white"}
        ${hover ? "hover:shadow-card-hover hover:border-accent-border/30 transition-all duration-200 cursor-pointer" : ""}
        ${onClick ? "text-left w-full" : ""}
        ${paddingStyles[padding]} ${className}`}
    >
      {children}
    </Component>
  );
}
