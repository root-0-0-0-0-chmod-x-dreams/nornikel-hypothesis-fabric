import type { Document, HypothesisSource } from "@/types";
import { DocumentList } from "./DocumentList";
import { ParagraphList } from "./ParagraphList";

interface ContextPanelProps {
  knowledgeDocuments: Document[];
  userDocuments: Document[];
  retrievedParagraphs?: HypothesisSource[];
  onRemove?: (id: string) => void;
  onClick?: (doc: Document) => void;
  onPreview?: (doc: Document) => void;
}

export function ContextPanel({
  knowledgeDocuments,
  userDocuments,
  retrievedParagraphs,
  onRemove,
  onClick,
  onPreview,
}: ContextPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1 mb-2">
          База знаний (GraphRAG + Qdrant)
        </h3>
        <DocumentList
          documents={knowledgeDocuments}
          onClick={onClick}
          onPreview={onPreview}
          emptyMessage="База знаний не загружена"
        />
      </div>

      {userDocuments.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1 mb-2">
            Ваши документы
          </h3>
          <DocumentList
            documents={userDocuments}
            onRemove={onRemove}
            onClick={onClick}
            onPreview={onPreview}
          />
        </div>
      )}

      {retrievedParagraphs && retrievedParagraphs.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1 mb-2">
            Использованные параграфы
          </h3>
          <ParagraphList paragraphs={retrievedParagraphs} />
        </div>
      )}
    </div>
  );
}
