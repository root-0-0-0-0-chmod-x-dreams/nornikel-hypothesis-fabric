import type { Document } from "@/types";
import { DocumentCard } from "./DocumentCard";
import { AttentionView } from "@/components/ui";
import { FileSearch } from "lucide-react";

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
    return (
      <AttentionView
        icon={<FileSearch size={24} />}
        title="Нет документов"
        description={emptyMessage}
        variant="gray"
        size="sm"
        className="py-6"
      />
    );
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
