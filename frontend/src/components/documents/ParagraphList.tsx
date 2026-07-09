import { useState } from "react";
import { FileText, ChevronDown, ChevronRight } from "lucide-react";
import type { HypothesisSource } from "@/types";
import { Badge, Spinner } from "@/components/ui";

function locationLabel(p: HypothesisSource): string | null {
  const parts: string[] = [];
  if (p.page != null) parts.push(`стр. ${p.page}`);
  if (p.paragraphIndex != null) parts.push(`§${p.paragraphIndex + 1}`);
  return parts.length ? parts.join(", ") : null;
}

function ParagraphItem({ paragraph }: { paragraph: HypothesisSource }) {
  const [open, setOpen] = useState(false);
  const [fullText, setFullText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const loc = locationLabel(paragraph);

  const toggle = async () => {
    if (!paragraph.chunkId) {
      setOpen((v) => !v);
      return;
    }
    if (fullText) {
      setOpen((v) => !v);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/sources/chunks/${encodeURIComponent(paragraph.chunkId)}`);
      if (res.ok) {
        const data = await res.json();
        setFullText(String(data.text ?? paragraph.excerpt ?? ""));
        setOpen(true);
      } else {
        setFullText(paragraph.excerpt ?? "Текст недоступен");
        setOpen(true);
      }
    } catch {
      setFullText(paragraph.excerpt ?? "Текст недоступен");
      setOpen(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-accent-border/40 bg-accent-bg/20 p-2.5">
      <button
        type="button"
        onClick={() => void toggle()}
        className="w-full flex items-start gap-2 text-left cursor-pointer"
      >
        <FileText size={14} className="text-accent mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-text leading-snug">{paragraph.title}</p>
          {loc && <p className="text-[10px] text-text-muted mt-0.5">{loc}</p>}
        </div>
        {paragraph.type && <Badge variant="info">{paragraph.type}</Badge>}
        {open ? <ChevronDown size={14} className="text-text-muted" /> : <ChevronRight size={14} className="text-text-muted" />}
      </button>
      {!open && paragraph.excerpt && (
        <p className="text-xs text-text-muted mt-2 pl-6 line-clamp-2">«{paragraph.excerpt}»</p>
      )}
      {loading && (
        <div className="pl-6 py-1">
          <Spinner size={14} />
        </div>
      )}
      {open && (fullText || paragraph.excerpt) && (
        <p className="text-xs text-text leading-relaxed mt-2 pl-6 whitespace-pre-wrap border-l-2 border-accent-border/50 ml-1">
          {fullText ?? paragraph.excerpt}
        </p>
      )}
    </div>
  );
}

export function ParagraphList({ paragraphs }: { paragraphs: HypothesisSource[] }) {
  return (
    <div className="flex flex-col gap-2">
      {paragraphs.map((p, i) => (
        <ParagraphItem key={`${p.chunkId ?? p.title}-${i}`} paragraph={p} />
      ))}
    </div>
  );
}
