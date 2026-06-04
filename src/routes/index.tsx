import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, FileCode2, GitBranch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/Navbar";
import { ReviewMockup } from "@/components/ReviewMockup";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CodeLens AI — AI Code Reviews, Instantly" },
      {
        name: "description",
        content:
          "Paste your code or drop a GitHub PR URL and get line-level feedback on bugs, security, and style in seconds.",
      },
      { property: "og:title", content: "CodeLens AI — AI Code Reviews, Instantly" },
      {
        property: "og:description",
        content: "Line-level AI code review for bugs, security, style, complexity and performance.",
      },
    ],
    links: [{ rel: "canonical", href: "/" }],
  }),
  component: Landing,
});

const features = [
  {
    icon: FileCode2,
    title: "Line-level feedback",
    desc: "Pinpoints exact lines with issues, not vague summaries.",
  },
  {
    icon: ShieldCheck,
    title: "5 issue categories",
    desc: "Bugs, security, style, complexity, and performance — all covered.",
  },
  {
    icon: GitBranch,
    title: "GitHub PR support",
    desc: "Drop a PR URL and review the full diff in one click.",
  },
];

function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <Navbar />

      {/* Animated gradient orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="bg-purple/30 animate-blob absolute -top-32 left-1/4 h-96 w-96 rounded-full blur-3xl" />
        <div className="bg-pink/25 animate-blob absolute top-20 right-1/4 h-96 w-96 rounded-full blur-3xl [animation-delay:3s]" />
        <div className="bg-cyan/20 animate-blob absolute top-72 left-1/3 h-80 w-80 rounded-full blur-3xl [animation-delay:6s]" />
      </div>

      <main className="relative mx-auto max-w-6xl px-4 pt-36 pb-24 sm:pt-44">
        {/* Hero */}
        <section className="text-center">
          <span className="glass animate-fade-in inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium text-muted-foreground">
            <span className="bg-gradient-brand h-1.5 w-1.5 rounded-full" />
            Powered by LangChain + LLMs
          </span>
          <h1 className="animate-fade-up mx-auto mt-6 max-w-3xl text-5xl font-extrabold tracking-tight sm:text-7xl">
            AI Code Reviews.{" "}
            <span className="text-gradient">Instantly.</span>
          </h1>
          <p className="animate-fade-up mx-auto mt-6 max-w-2xl text-lg text-muted-foreground [animation-delay:0.1s]">
            Paste your code or drop a GitHub PR URL. Get line-level feedback on bugs, security, and
            style in seconds.
          </p>
          <div className="animate-fade-up mt-9 flex flex-wrap items-center justify-center gap-3 [animation-delay:0.2s]">
            <Button asChild variant="hero" size="xl">
              <Link to="/app">
                Try it free <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="heroOutline" size="xl">
              <a href="https://github.com" target="_blank" rel="noreferrer">
                View on GitHub
              </a>
            </Button>
          </div>
        </section>

        {/* Floating mockup */}
        <section className="animate-fade-up relative mx-auto mt-20 max-w-2xl [animation-delay:0.35s] [perspective:1500px]">
          <div className="bg-gradient-brand absolute -inset-6 -z-10 rounded-[2rem] opacity-30 blur-3xl" />
          <div className="animate-float [transform:rotateX(8deg)_rotateZ(-1.5deg)]">
            <ReviewMockup />
          </div>
        </section>

        {/* Features */}
        <section className="mt-32">
          <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
            Reviews that actually <span className="text-gradient">help</span>
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div
                key={f.title}
                className="glass group rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-glow"
              >
                <div className="bg-gradient-brand shadow-glow flex h-12 w-12 items-center justify-center rounded-xl">
                  <f.icon className="h-6 w-6 text-primary-foreground" />
                </div>
                <h3 className="mt-5 text-lg font-bold">{f.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="glass relative mt-28 overflow-hidden rounded-3xl p-10 text-center sm:p-16">

          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Ship cleaner code, faster.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-muted-foreground">
            Run your first review in under ten seconds. No setup required.
          </p>
          <Button asChild variant="hero" size="xl" className="mt-8">
            <Link to="/app">
              Start reviewing <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </section>
      </main>

      <footer className="relative border-t border-border/50 py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} CodeLens AI
      </footer>
    </div>
  );
}
