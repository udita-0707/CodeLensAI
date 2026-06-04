import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Navbar } from "@/components/Navbar";
import { InputPanel } from "@/components/review/InputPanel";
import { ResultsPanel } from "@/components/review/ResultsPanel";
import { type ReviewResult } from "@/lib/review-data";

const API_BASE = "http://localhost:8000";

export const Route = createFileRoute("/app")({
  head: () => ({
    meta: [
      { title: "Review — CodeLens AI" },
      {
        name: "description",
        content: "Paste code or a GitHub PR URL and get instant line-level AI review.",
      },
    ],
    links: [{ rel: "canonical", href: "/app" }],
  }),
  component: AppPage,
});

function AppPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);

  // Lifted state — InputPanel reports its current values via onReview callback
  const handleReview = async (
    tab: "code" | "pr",
    code: string,
    language: string,
    prUrl: string,
  ) => {
    setLoading(true);
    setResult(null);

    try {
      let res: Response;

      if (tab === "code") {
        // POST /review/code
        res = await fetch(`${API_BASE}/review/code`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, language }),
        });
      } else {
        // POST /review/pr
        res = await fetch(`${API_BASE}/review/pr`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pr_url: prUrl }),
        });
      }

      if (!res.ok) {
        // Try to surface the backend error message
        let detail = `Server error ${res.status}`;
        try {
          const errBody = await res.json();
          if (errBody?.detail) detail = errBody.detail;
        } catch {
          // ignore JSON parse failure on error response
        }
        throw new Error(detail);
      }

      const data: ReviewResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      toast.error("Review failed", {
        description: message,
        duration: 6000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <Navbar />
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="bg-purple/20 animate-blob absolute -top-20 left-0 h-80 w-80 rounded-full blur-3xl" />
        <div className="bg-cyan/15 animate-blob absolute right-0 bottom-0 h-80 w-80 rounded-full blur-3xl [animation-delay:4s]" />
      </div>

      <main className="relative mx-auto max-w-6xl px-4 pt-28 pb-16">
        <div className="animate-fade-up mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Review your <span className="text-gradient">code</span>
          </h1>
          <p className="mt-2 text-muted-foreground">
            Get line-level feedback on bugs, security, style, complexity and performance.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <InputPanel loading={loading} onReview={handleReview} />
          <ResultsPanel result={result} loading={loading} />
        </div>
      </main>
    </div>
  );
}
