import Link from "next/link";
import { Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { SITE } from "@/lib/content";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur supports-[backdrop-filter]:bg-[var(--color-background)]/80 border-b border-[var(--color-border)]">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="font-mono text-lg font-bold">
          <span className="text-[var(--color-accent)]">[</span>
          {" "}rag-forge{" "}
          <span className="text-[var(--color-accent)]">]</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm text-[var(--color-muted)]">
          <Link href="#features" className="hover:text-[var(--color-foreground)] transition-colors">
            Features
          </Link>
          <Link href="#rmm" className="hover:text-[var(--color-foreground)] transition-colors">
            RMM
          </Link>
          <Link href="#quick-start" className="hover:text-[var(--color-foreground)] transition-colors">
            Quick Start
          </Link>
          <Link href="#templates" className="hover:text-[var(--color-foreground)] transition-colors">
            Templates
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={SITE.github}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View RAG-Forge on GitHub"
            className="hidden sm:inline-flex items-center gap-2 px-3 h-9 rounded-md border border-[var(--color-border)] hover:bg-[var(--color-card)] text-sm font-mono"
          >
            <Github className="h-4 w-4" aria-hidden="true" />
            <span>GitHub</span>
          </a>
          <ThemeToggle />
          <Button size="sm" asChild>
            <Link href="#quick-start">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
