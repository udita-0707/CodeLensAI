import { useMemo, useState } from "react";
import { Github, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

type Tab = "code" | "pr";

const LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "Ruby"];

const SAMPLE = `def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    row = db.execute(query)
    user = row.fetchone()
    name = user.profile.name
    return name`;

export function InputPanel({
  loading,
  onReview,
}: {
  loading: boolean;
  onReview: (tab: "code" | "pr", code: string, language: string, prUrl: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("code");
  const [code, setCode] = useState(SAMPLE);
  const [lang, setLang] = useState("Python");
  const [url, setUrl] = useState("");

  const lineCount = useMemo(() => Math.max(code.split("\n").length, 12), [code]);

  return (
    <div className="glass flex flex-col rounded-2xl p-4 sm:p-5">
      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-secondary/60 p-1">
        {([
          ["code", "Paste Code"],
          ["pr", "GitHub PR URL"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              tab === key
                ? "bg-gradient-brand text-primary-foreground shadow-glow"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-4 flex-1">
        {tab === "code" ? (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground">Language</label>
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="rounded-lg border border-border bg-input px-3 py-1.5 text-sm font-medium outline-none focus:ring-1 focus:ring-ring"
              >
                {LANGUAGES.map((l) => (
                  <option key={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="relative flex overflow-hidden rounded-xl border border-border bg-[oklch(0.11_0.02_280)]">
              <div className="select-none border-r border-border/60 px-3 py-3 text-right font-mono text-xs leading-6 text-muted-foreground/60">
                {Array.from({ length: lineCount }, (_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                spellCheck={false}
                placeholder="Paste your code here…"
                className="h-72 flex-1 resize-none bg-transparent px-3 py-3 font-mono text-sm leading-6 text-foreground outline-none"
              />
            </div>
          </div>
        ) : (
          <div>
            <label className="text-xs font-medium text-muted-foreground">Pull request URL</label>
            <div className="mt-2 flex items-center gap-2 rounded-xl border border-border bg-input px-3">
              <Github className="h-4 w-4 shrink-0 text-muted-foreground" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo/pull/123"
                className="w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground/60"
              />
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              We'll fetch the full diff and review every changed line.
            </p>
          </div>
        )}
      </div>

      <Button
        variant="hero"
        size="lg"
        onClick={() => onReview(tab, code, lang, url)}
        disabled={loading}
        className="relative mt-5 w-full overflow-hidden"
      >
        {loading && <span className="shimmer-bg absolute inset-0" />}
        <span className="relative inline-flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          {loading ? "Reviewing…" : "Review Code"}
        </span>
      </Button>
    </div>
  );
}
