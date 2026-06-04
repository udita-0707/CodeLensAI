import { useState } from "react";
import { ChevronRight, Lightbulb } from "lucide-react";
import { categoryLabels, severityMeta, type ReviewIssue } from "@/lib/review-data";

export function IssueCard({ issue, index }: { issue: ReviewIssue; index: number }) {
  const [open, setOpen] = useState(false);
  const meta = severityMeta[issue.severity];

  return (
    <div
      className={`glass animate-fade-up rounded-xl border-l-4 p-4 ${meta.border}`}
      style={{ animationDelay: `${index * 0.08}s` }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.badge}`}>
          {meta.label}
        </span>
        <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
          {categoryLabels[issue.category]}
        </span>
        <span className="ml-auto rounded-full bg-muted px-2.5 py-0.5 font-mono text-xs text-muted-foreground">
          {issue.line ? `Line ${issue.line}` : "General"}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed">{issue.description}</p>

      <button
        onClick={() => setOpen((o) => !o)}
        className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary transition-colors hover:brightness-125"
      >
        <Lightbulb className="h-4 w-4" />
        Suggestion
        <ChevronRight className={`h-4 w-4 transition-transform ${open ? "rotate-90" : ""}`} />
      </button>

      <div
        className={`grid transition-all duration-300 ${open ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}
      >
        <div className="overflow-hidden">
          <p className="rounded-lg bg-secondary/60 p-3 text-sm leading-relaxed text-muted-foreground">
            {issue.suggestion}
          </p>
        </div>
      </div>
    </div>
  );
}
