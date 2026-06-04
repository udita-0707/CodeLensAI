import { Link } from "@tanstack/react-router";
import { Sparkles } from "lucide-react";

export function Navbar() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4">
      <nav className="glass flex w-full max-w-5xl items-center justify-between rounded-2xl px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="bg-gradient-brand flex h-8 w-8 items-center justify-center rounded-lg shadow-glow">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </span>
          <span className="text-base font-bold tracking-tight">CodeLens AI</span>
        </Link>
        <div className="flex items-center gap-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hidden text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline"
          >
            GitHub
          </a>
          <Link
            to="/app"
            className="bg-gradient-brand rounded-lg px-4 py-2 text-sm font-semibold text-primary-foreground shadow-glow transition-all hover:brightness-110"
          >
            Launch app
          </Link>
        </div>
      </nav>
    </header>
  );
}
