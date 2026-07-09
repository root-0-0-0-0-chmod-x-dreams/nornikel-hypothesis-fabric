import { useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, FileText, Lightbulb } from "lucide-react";
import type { Hypothesis, HypothesisSource } from "@/types";
import { Badge, Card, Progress, Spinner } from "@/components/ui";
import { noveltyLabel, normalizeSources, impactLabel, impactLevel } from "@/lib/hypothesis";

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  selected?: boolean;
  onSelect?: () => void;
}

const impactVariant: Record<ReturnType<typeof impactLevel>, "accent" | "warning" | "default"> = {
  high: "accent",
  medium: "warning",
  low: "default",
};

function locationLabel(source: HypothesisSource): string | null {
  const parts: string[] = [];
  if (source.page != null) parts.push(`стр. ${source.page}`);
  if (source.paragraphIndex != null) parts.push(`§${source.paragraphIndex + 1}`);
  return parts.length ? parts.join(", ") : null;
}

function SourceItem({ source }: { source: HypothesisSource }) {
  const [expanded, setExpanded] = useState(false);
  const [fullText, setFullText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const loc = locationLabel(source);
  const isExternal = source.url?.startsWith("http");

  const openChunk = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!source.chunkId) return;
    if (fullText) {
      setExpanded((v) => !v);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/sources/chunks/${encodeURIComponent(source.chunkId)}`);
      if (res.ok) {
        const data = await res.json();
        setFullText(String(data.text ?? data.excerpt ?? source.excerpt ?? ""));
        setExpanded(true);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <li className="rounded-lg border border-border/70 bg-white/40 p-2.5 space-y-1.5">
      <div className="flex items-start gap-2">
        {source.chunkId ? (
          <button
            type="button"
            onClick={openChunk}
            className="flex items-start gap-2 text-xs text-accent hover:underline text-left cursor-pointer"
          >
            <FileText size={12} className="mt-0.5 flex-shrink-0 opacity-70" />
            <span>{source.title}</span>
          </button>
        ) : isExternal && source.url ? (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-start gap-2 text-xs text-accent hover:underline group"
          >
            <ExternalLink size={12} className="mt-0.5 flex-shrink-0 opacity-60 group-hover:opacity-100" />
            <span>{source.title}</span>
          </a>
        ) : (
          <span className="text-xs text-text leading-relaxed">{source.title}</span>
        )}
        {source.type && source.type !== "reference" && (
          <Badge variant="default" className="ml-auto flex-shrink-0">{source.type}</Badge>
        )}
      </div>
      {loc && <p className="text-[10px] text-text-muted pl-5">{loc}</p>}
      {source.excerpt && !expanded && (
        <p className="text-xs text-text-muted leading-relaxed pl-5 line-clamp-3">«{source.excerpt}»</p>
      )}
      {loading && (
        <div className="pl-5 py-1">
          <Spinner size={14} />
        </div>
      )}
      {expanded && fullText && (
        <p className="text-xs text-text leading-relaxed pl-5 whitespace-pre-wrap border-l-2 border-accent-border/50 ml-2">
          {fullText}
        </p>
      )}
    </li>
  );
}

export function HypothesisCard({ hypothesis, selected, onSelect }: HypothesisCardProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const confidencePct = Math.round((hypothesis.confidence ?? 0.7) * 100);
  const sources = hypothesis.sourceDetails?.length
    ? hypothesis.sourceDetails
    : normalizeSources(hypothesis.sources);

  return (
    <Card
      padding="lg"
      hover={!!onSelect}
      onClick={onSelect}
      className={`transition-all ${selected ? "ring-2 ring-accent/40 border-accent-border" : ""}`}
    >
      <div className="flex gap-3 items-start">
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-accent-bg text-accent flex items-center justify-center">
          <Lightbulb size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text leading-snug">{hypothesis.title}</h3>
          <p className="text-sm text-text-muted mt-2 leading-relaxed">{hypothesis.description}</p>

          <div className="flex flex-wrap gap-2 mt-3">
            <Badge variant={impactVariant[impactLevel(hypothesis)]}>{impactLabel(hypothesis)}</Badge>
            <Badge variant="default">{noveltyLabel(hypothesis.novelty)}</Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            <div className="rounded-xl border border-accent-amber-border bg-accent-amber-bg/50 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-accent-amber mb-1.5">
                Технические риски
              </p>
              <p className="text-xs text-text leading-relaxed">{hypothesis.risks.technical}</p>
            </div>
            <div className="rounded-xl border border-accent-green-border bg-accent-green-bg/50 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-accent-green mb-1.5">
                Экономические риски
              </p>
              <p className="text-xs text-text leading-relaxed">{hypothesis.risks.economic}</p>
            </div>
          </div>

          <div className="mt-4">
            <Progress
              value={confidencePct}
              label="УВЕРЕННОСТЬ МОДЕЛИ"
              showValue
              size="sm"
              color="accent"
            />
          </div>

          <div className="mt-4 flex items-start gap-2">
            <span className="w-2 h-2 rounded-full bg-accent mt-1.5 flex-shrink-0" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">
                Ожидаемая ценность
              </p>
              <p className="text-xs text-text mt-1 leading-relaxed">{hypothesis.expectedValue}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setSourcesOpen((v) => !v);
            }}
            className="mt-4 flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover transition-colors"
          >
            {sourcesOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            Научное обоснование и источники
          </button>

          {sourcesOpen && (
            <div className="mt-3 pl-3 border-l-2 border-accent-border space-y-3 animate-fade-in">
              {hypothesis.rationale && (
                <p className="text-xs text-text-muted leading-relaxed">{hypothesis.rationale}</p>
              )}
              {hypothesis.mechanism && (
                <p className="text-xs text-text leading-relaxed">
                  <span className="font-medium text-text">Механизм: </span>
                  {hypothesis.mechanism}
                </p>
              )}
              <ul className="space-y-2 list-none pl-0">
                {sources.map((s, i) => (
                  <SourceItem key={`${s.chunkId ?? s.title}-${i}`} source={s} />
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
