import { type TextareaHTMLAttributes, forwardRef } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-text-muted">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={`w-full px-3.5 py-2.5 text-sm rounded-xl border bg-white/80 backdrop-blur-sm resize-none
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

Textarea.displayName = "Textarea";
