import { ArrowRight, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/copy-button";
import { HERO, SITE } from "@/lib/content";

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-20 pb-24 sm:pt-32 sm:pb-32">
      {/* Subtle dot grid background */}
      <div
        className="absolute inset-0 -z-10 opacity-[0.15]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, var(--color-foreground) 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tighter leading-[1.05]">
            {HERO.headline}
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-[var(--color-muted)] leading-relaxed max-w-3xl mx-auto">
            {HERO.subheadline}
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] font-mono text-sm">
              <span className="text-[var(--color-muted)]">$</span>
              <span>{HERO.installCommand}</span>
              <CopyButton value={HERO.installCommand} className="ml-2" />
            </div>
            <Button variant="outline" size="lg" asChild>
              <a href={SITE.github} target="_blank" rel="noopener noreferrer">
                <Github className="h-4 w-4" />
                View on GitHub
                <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>

        {/* Hero artifact: terminal mock */}
        <div className="mt-16 mx-auto max-w-4xl">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] overflow-hidden shadow-2xl">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-background)]">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-500/60" />
                <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
                <div className="h-3 w-3 rounded-full bg-green-500/60" />
              </div>
              <span className="text-xs font-mono text-[var(--color-muted)] ml-2">rag-forge audit</span>
            </div>
            <div className="p-6 font-mono text-sm space-y-2">
              <div className="text-[var(--color-muted)]">$ rag-forge audit --golden-set qa.json</div>
              <div className="text-[var(--color-muted)]">Running RAGAS evaluation on 50 samples...</div>
              <div className="mt-4 space-y-1">
                <div className="flex justify-between">
                  <span>faithfulness</span>
                  <span className="text-[var(--color-accent)]">0.91 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>context_relevance</span>
                  <span className="text-[var(--color-accent)]">0.84 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>answer_relevance</span>
                  <span className="text-[var(--color-accent)]">0.88 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>recall_at_k</span>
                  <span className="text-red-400">0.62 FAIL</span>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/30">
                    RMM-3
                  </span>
                  <span className="text-[var(--color-muted)]">Better Trust</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
