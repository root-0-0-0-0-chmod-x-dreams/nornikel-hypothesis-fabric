import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-text-muted">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`w-full px-3.5 py-2.5 text-sm rounded-xl border bg-white/80 backdrop-blur-sm
            placeholder:text-text-muted/50 transition-all duration-200
            focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent-border focus:bg-white
            ${error ? "border-red-400 focus:ring-red-400/20 focus:border-red-400" : "border-border"}
            shadow-sm ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";
