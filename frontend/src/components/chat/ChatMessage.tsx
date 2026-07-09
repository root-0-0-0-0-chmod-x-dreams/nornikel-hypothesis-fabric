import { Bot, User } from "lucide-react";
import { TypingDots } from "@/components/ui";
import { HypothesisList } from "@/components/hypothesis";
import { AgentPipeline } from "./AgentPipeline";
import type { ChatMessage as ChatMessageType, Hypothesis } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
  selectedHypothesisId?: string;
  onSelectHypothesis?: (hypothesis: Hypothesis) => void;
  generationSettings?: { maxHypotheses: number; agentCycleDepth: number };
}

export function ChatMessage({
  message,
  selectedHypothesisId,
  onSelectHypothesis,
  generationSettings,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const hasHypotheses = !isUser && message.hypotheses && message.hypotheses.length > 0;
  const hasAgentSteps = !isUser && message.agentSteps && message.agentSteps.length > 0;
  const pipelineRunning = message.isStreaming && hasAgentSteps;
  const showTypingDots = message.isStreaming && !message.content && !hasAgentSteps;

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-sm
          ${isUser ? "bg-accent/90 backdrop-blur-sm text-white" : "glass text-text-muted"}`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`flex flex-col gap-3 min-w-0 ${isUser ? "items-end max-w-[75%]" : "items-start w-full max-w-4xl"}`}>
        {hasAgentSteps && (
          <AgentPipeline
            steps={message.agentSteps!}
            hypothesisCount={generationSettings?.maxHypotheses}
            cycleDepth={generationSettings?.agentCycleDepth}
            isRunning={pipelineRunning}
            elapsedSeconds={message.generationElapsed}
          />
        )}

        {(message.content || showTypingDots) && (
          <div
            className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm
              ${isUser
                ? "bg-accent/90 backdrop-blur-sm text-white rounded-br-md"
                : "glass text-text rounded-bl-md"
              }`}
          >
            {showTypingDots ? (
              <TypingDots className="py-1" />
            ) : (
              <div className="whitespace-pre-wrap">{message.content}</div>
            )}
          </div>
        )}

        {hasHypotheses && (
          <HypothesisList
            hypotheses={message.hypotheses!}
            selectedId={selectedHypothesisId}
            onSelect={onSelectHypothesis}
          />
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
