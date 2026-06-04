import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { InputPanel } from "@/components/review/InputPanel";
import { ResultsPanel } from "@/components/review/ResultsPanel";
import { mockReview, type ReviewResult } from "@/lib/review-data";

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

  const handleReview = async () => {
    setLoading(true);
    setResult(null);

    // TODO: Replace this mock with the real API call:
    //   const res = await fetch("/api/review/code", {
    //     method: "POST",
    //     headers: { "Content-Type": "application/json" },
    //     body: JSON.stringify({ code, language }),
    //   });
    //   const data: ReviewResult = await res.json();
    //   setResult(data);
    await new Promise((r) => setTimeout(r, 1800));
    setResult(mockReview);
    setLoading(false);
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
