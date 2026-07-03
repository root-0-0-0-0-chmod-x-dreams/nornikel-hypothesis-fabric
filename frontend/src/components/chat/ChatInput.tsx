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
    <form onSubmit={handleSubmit} className="flex items-end gap-2 p-4 border-t border-border bg-white">
      <Tooltip content="Прикрепить файл или ссылку">
        <button
          type="button"
          onClick={onAttach}
          disabled={disabled}
          className="p-2 rounded-lg hover:bg-gray-100 text-text-muted hover:text-accent transition-colors cursor-pointer disabled:opacity-50"
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
        className="flex-1 resize-none px-3.5 py-2.5 text-sm rounded-xl border border-border
          placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent-border
          transition-colors duration-150 max-h-40"
      />
      <Tooltip content="Отправить (Enter)">
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="p-2.5 rounded-xl bg-accent text-white hover:bg-accent-hover transition-colors
            disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <Send size={18} />
        </button>
      </Tooltip>
    </form>
  );
}
