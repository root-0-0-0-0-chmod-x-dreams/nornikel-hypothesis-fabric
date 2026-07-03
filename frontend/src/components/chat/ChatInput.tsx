import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import { Send, Plus } from "lucide-react";
import { Tooltip } from "@/components/ui";

interface ChatInputProps {
  onSend: (text: string) => void;
  onAttach: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onAttach,
  disabled = false,
  placeholder = "Введите запрос или опишите технологическую проблему...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 p-4 border-t border-border glass-strong">
      <Tooltip content="Прикрепить файл или ссылку">
        <button
          type="button"
          onClick={onAttach}
          disabled={disabled}
          className="p-2 rounded-xl hover:bg-black/5 text-text-muted hover:text-accent transition-colors cursor-pointer disabled:opacity-50"
        >
          <Plus size={18} />
        </button>
      </Tooltip>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 resize-none px-4 py-2.5 text-sm rounded-2xl border border-border bg-white/70 backdrop-blur-sm
          placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent-border focus:bg-white
          transition-all duration-200 max-h-40 shadow-sm"
      />
      <Tooltip content="Отправить (Enter)">
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="p-2.5 rounded-xl bg-accent/90 backdrop-blur-sm text-white hover:bg-accent transition-all duration-200
            disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-button hover:shadow-button-hover"
        >
          <Send size={18} />
        </button>
      </Tooltip>
    </form>
  );
}
