import { Bot, User } from "lucide-react";
import { TypingDots } from "@/components/ui";
import type { ChatMessage as ChatMessageType } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? "bg-accent text-white" : "bg-gray-100 text-text-muted"}`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`flex flex-col gap-2 max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed
            ${isUser
              ? "bg-accent text-white rounded-br-md"
              : "bg-gray-100 text-text rounded-bl-md"
            }`}
        >
          {message.isStreaming && !message.content ? (
            <TypingDots className="py-1" />
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
          )}
        </div>
        {message.isStreaming && message.content && (
          <span className="inline-block w-2 h-4 bg-accent animate-pulse rounded-sm ml-1" />
        )}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.attachments.map((doc) => (
              <span key={doc.id} className="inline-flex items-center gap-1 px-2.5 py-1 text-xs bg-accent-bg text-accent rounded-full">
                {doc.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
