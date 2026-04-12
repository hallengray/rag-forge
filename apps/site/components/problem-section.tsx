import { Card } from "@/components/ui/card";
import { PROBLEMS } from "@/lib/content";

export function ProblemSection() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            The RAG quality crisis
          </h2>
          <p className="mt-6 text-lg text-[var(--color-muted)]">
            RAG has become the dominant architecture for enterprise AI. Yet the ecosystem
            suffers from a critical gap between building RAG pipelines and knowing whether
            they actually work.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6">
          {PROBLEMS.map((problem) => (
            <Card key={problem.stat}>
              <div className="font-mono text-5xl font-bold text-[var(--color-accent)]">
                {problem.stat}
              </div>
              <p className="mt-4 text-[var(--color-foreground)]">{problem.label}</p>
              <p className="mt-3 text-xs text-[var(--color-muted)] font-mono">
                {problem.source}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
