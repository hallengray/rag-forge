import { ArrowRight, Github, Sparkles } from "lucide-react";
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
          <a
            href={SITE.releaseNotes}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 font-mono text-xs text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-colors"
          >
            <Sparkles className="h-3 w-3" />
            <span>{HERO.versionBadge}</span>
            <ArrowRight className="h-3 w-3" />
          </a>
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

        {/* Hero artifact: v0.1.3 terminal mock with banner + per-sample stream */}
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
            <div className="p-6 font-mono text-xs sm:text-sm space-y-1 leading-relaxed">
              <div className="text-[var(--color-muted)]">$ rag-forge audit --golden-set eval/golden_set.json --judge claude</div>
              <div className="mt-3 text-[var(--color-foreground)]">RAG-Forge Audit</div>
              <div className="text-[var(--color-foreground)]">===============</div>
              <div><span className="text-[var(--color-muted)]">  Samples:         </span>19</div>
              <div><span className="text-[var(--color-muted)]">  Metrics:         </span>4 (faithfulness, context_relevance, answer_relevance, hallucination)</div>
              <div><span className="text-[var(--color-muted)]">  Judge calls:     </span>76 total</div>
              <div><span className="text-[var(--color-muted)]">  Judge model:     </span>claude-sonnet-4-20250514</div>
              <div><span className="text-[var(--color-muted)]">  Estimated cost:  </span>~$1.25 USD</div>
              <div className="text-[var(--color-muted)]">---</div>
              <div>[ 1/19] [query redacted]                  faith=0.92  ctx=0.85  ans=0.91  hall=0.95  <span className="text-[var(--color-accent)]">OK</span>  (8.2s)</div>
              <div>[ 2/19] [query redacted]                  faith=0.88  ctx=0.79  ans=0.90  hall=0.93  <span className="text-[var(--color-accent)]">OK</span>  (9.1s)</div>
              <div>[ 3/19] [query redacted]                  faith=0.00  ctx=0.00  ans=0.78  hall=0.85  <span className="text-yellow-400">WARN 2 skipped</span>  (11.4s)</div>
              <div className="text-[var(--color-muted)]">  ...</div>
              <div className="text-[var(--color-muted)]">---</div>
              <div>Audit complete in 9m 23s</div>
              <div>Scored: <span className="text-[var(--color-accent)]">72</span>    Skipped: <span className="text-yellow-400">4</span></div>
              <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
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
