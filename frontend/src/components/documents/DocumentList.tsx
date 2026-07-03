import type { Document } from "@/types";
import { DocumentCard } from "./DocumentCard";

interface DocumentListProps {
  documents: Document[];
  onRemove?: (id: string) => void;
  onClick?: (doc: Document) => void;
  onPreview?: (doc: Document) => void;
  emptyMessage?: string;
}

export function DocumentList({
  documents,
  onRemove,
  onClick,
  onPreview,
  emptyMessage = "Нет загруженных документов",
}: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-text-muted text-center py-4">{emptyMessage}</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.id}
          document={doc}
          onRemove={onRemove}
          onClick={onClick}
          onPreview={onPreview}
        />
      ))}
    </div>
  );
}
