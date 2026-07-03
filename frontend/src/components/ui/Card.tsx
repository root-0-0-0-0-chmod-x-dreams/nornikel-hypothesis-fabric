import { type ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingStyles = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export function Card({ children, className = "", onClick, hover = false, padding = "md" }: CardProps) {
  const Component = onClick ? "button" : "div";
  return (
    <Component
      onClick={onClick}
      className={`bg-white rounded-xl border border-border shadow-sm
        ${hover ? "hover:shadow-md hover:border-accent-border/50 transition-all duration-200 cursor-pointer" : ""}
        ${onClick ? "text-left w-full" : ""}
        ${paddingStyles[padding]} ${className}`}
    >
      {children}
    </Component>
  );
}
