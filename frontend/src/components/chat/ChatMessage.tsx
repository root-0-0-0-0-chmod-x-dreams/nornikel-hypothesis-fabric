import { Bot, User } from "lucide-react";
import { TypingDots } from "@/components/ui";
import type { ChatMessage as ChatMessageType } from "@/types";
import { HypothesisCard } from "./HypothesisCard";

interface ChatMessageProps {
  message: ChatMessageType;
  onSourceClick?: (source: string) => void;
}

export function ChatMessage({ message, onSourceClick }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-sm
          ${isUser ? "bg-accent/90 backdrop-blur-sm text-white" : "glass text-text-muted"}`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`flex flex-col gap-2 ${isUser ? "items-end max-w-[75%]" : "items-start w-full"}`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm
            ${isUser
              ? "bg-accent/90 backdrop-blur-sm text-white rounded-br-md"
              : "glass text-text rounded-bl-md"
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
        {!isUser && message.hypotheses && message.hypotheses.length > 0 && (
          <div className="flex flex-col gap-3 w-full mt-2">
            {message.hypotheses.map((h) => (
              <HypothesisCard key={h.id} hypothesis={h} onSourceClick={onSourceClick} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
