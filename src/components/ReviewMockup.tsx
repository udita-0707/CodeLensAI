import { mockReview, severityMeta } from "@/lib/review-data";

export function ReviewMockup() {
  return (
    <div className="glass shadow-glow w-full overflow-hidden rounded-2xl p-5 text-left">
      <div className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <div className="relative grid h-14 w-14 place-items-center rounded-full">
            <svg className="absolute inset-0 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" className="text-muted/40" />
              <circle
                cx="18" cy="18" r="16" fill="none" stroke="var(--warning)" strokeWidth="3"
                strokeDasharray={`${mockReview.quality_score} 100`} pathLength={100} strokeLinecap="round"
              />
            </svg>
            <span className="text-lg font-bold text-warning">{mockReview.quality_score}</span>
          </div>
          <div>
            <p className="text-sm font-semibold">Quality score</p>
            <p className="text-xs text-muted-foreground">main.py · 124 lines</p>
          </div>
        </div>
        <span className="rounded-full bg-warning/15 px-3 py-1 text-xs font-semibold text-warning">
          Needs work
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {mockReview.issues.slice(0, 3).map((issue, i) => (
          <div
            key={i}
            className={`rounded-xl border-l-2 bg-secondary/40 p-3 ${severityMeta[issue.severity].border}`}
          >
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${severityMeta[issue.severity].dot}`} />
              <span className="text-xs font-semibold">{severityMeta[issue.severity].label}</span>
              <span className="ml-auto font-mono text-xs text-muted-foreground">
                {issue.line ? `L${issue.line}` : "—"}
              </span>
            </div>
            <p className="mt-1.5 line-clamp-1 text-xs text-muted-foreground">{issue.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
