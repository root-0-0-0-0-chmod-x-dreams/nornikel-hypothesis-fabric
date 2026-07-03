import { useEffect, useRef, type ReactNode } from "react";
import type { ChatMessage as ChatMessageType } from "@/types";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

interface ChatContainerProps {
  messages: ChatMessageType[];
  onSend: (text: string) => void;
  onAttach: () => void;
  disabled?: boolean;
  emptyState?: ReactNode;
}

export function ChatContainer({
  messages,
  onSend,
  onAttach,
  disabled = false,
  emptyState,
}: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && emptyState ? (
          <div className="flex items-center justify-center h-full">{emptyState}</div>
        ) : (
          <div className="flex flex-col gap-6 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={onSend} onAttach={onAttach} disabled={disabled} />
    </div>
  );
}
