export type Severity = "critical" | "warning" | "info";
export type Category = "bug" | "security" | "style" | "complexity" | "perf";

export interface ReviewIssue {
  severity: Severity;
  category: Category;
  line: number | null;
  description: string;
  suggestion: string;
}

export interface ReviewResult {
  quality_score: number;
  summary: string;
  issues: ReviewIssue[];
}

// Mock data so the results panel is fully interactive without a backend.
export const mockReview: ReviewResult = {
  quality_score: 72,
  summary:
    "Solid structure overall, but a few correctness and security issues should be addressed before shipping.",
  issues: [
    {
      severity: "critical",
      category: "security",
      line: 24,
      description:
        "User input is concatenated directly into a SQL query, exposing the endpoint to SQL injection.",
      suggestion:
        "Use parameterized queries or an ORM. e.g. db.query('SELECT * FROM users WHERE id = $1', [userId]).",
    },
    {
      severity: "critical",
      category: "bug",
      line: 41,
      description:
        "Potential null dereference: `user.profile` may be undefined when the account is newly created.",
      suggestion:
        "Guard with optional chaining and a fallback: const name = user?.profile?.name ?? 'Guest'.",
    },
    {
      severity: "warning",
      category: "perf",
      line: 88,
      description:
        "A nested loop re-fetches the same data on every iteration, causing O(n²) network calls.",
      suggestion:
        "Hoist the fetch out of the loop and build a lookup map once before iterating.",
    },
    {
      severity: "info",
      category: "style",
      line: null,
      description:
        "Inconsistent naming: some functions use camelCase while others use snake_case.",
      suggestion:
        "Pick one convention (camelCase for JS/TS) and apply it across the module for readability.",
    },
  ],
};

export const severityMeta: Record<
  Severity,
  { label: string; border: string; dot: string; badge: string }
> = {
  critical: {
    label: "Critical",
    border: "border-l-destructive",
    dot: "bg-destructive",
    badge: "bg-destructive/15 text-destructive",
  },
  warning: {
    label: "Warning",
    border: "border-l-warning",
    dot: "bg-warning",
    badge: "bg-warning/15 text-warning",
  },
  info: {
    label: "Info",
    border: "border-l-info",
    dot: "bg-info",
    badge: "bg-info/15 text-info",
  },
};

export const categoryLabels: Record<Category, string> = {
  bug: "Bug",
  security: "Security",
  style: "Style",
  complexity: "Complexity",
  perf: "Perf",
};
