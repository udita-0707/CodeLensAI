import { useMemo, useState } from "react";
import { ScanSearch } from "lucide-react";
import {
  categoryLabels,
  type Category,
  type ReviewResult,
} from "@/lib/review-data";
import { ScoreBadge } from "./ScoreBadge";
import { IssueCard } from "./IssueCard";

type Filter = "all" | Category;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "bug", label: "Bugs" },
  { key: "security", label: "Security" },
  { key: "style", label: "Style" },
  { key: "complexity", label: "Complexity" },
  { key: "perf", label: "Perf" },
];

export function ResultsPanel({
  result,
  loading,
}: {
  result: ReviewResult | null;
  loading: boolean;
}) {
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = useMemo(() => {
    if (!result) return [];
    return filter === "all"
      ? result.issues
      : result.issues.filter((i) => i.category === filter);
  }, [result, filter]);

  if (loading) {
    return (
      <div className="glass space-y-4 rounded-2xl p-6">
        <div className="shimmer-bg h-28 w-28 rounded-full" />
        <div className="shimmer-bg h-4 w-3/4 rounded" />
        <div className="shimmer-bg h-4 w-1/2 rounded" />
        <div className="shimmer-bg h-24 w-full rounded-xl" />
        <div className="shimmer-bg h-24 w-full rounded-xl" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="glass flex min-h-[420px] flex-col items-center justify-center rounded-2xl p-8 text-center">
        <div className="bg-gradient-brand/20 flex h-16 w-16 items-center justify-center rounded-2xl border border-border">
          <ScanSearch className="text-gradient h-8 w-8" style={{ color: "var(--purple)" }} />
        </div>
        <p className="mt-5 text-base font-semibold">No review yet</p>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Paste your code on the left to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="glass animate-fade-in rounded-2xl p-5 sm:p-6">
      <div className="flex items-center gap-5">
        <ScoreBadge score={result.quality_score} />
        <p className="text-sm leading-relaxed text-muted-foreground">{result.summary}</p>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all ${
              filter === f.key
                ? "bg-gradient-brand text-primary-foreground shadow-glow"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-5 space-y-3">
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No {filter === "all" ? "" : categoryLabels[filter as Category].toLowerCase()} issues
            found. 🎉
          </p>
        ) : (
          filtered.map((issue, i) => <IssueCard key={i} issue={issue} index={i} />)
        )}
      </div>
    </div>
  );
}
