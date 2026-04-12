import { Card } from "@/components/ui/card";
import { PILLARS } from "@/lib/content";

export function FeatureGrid() {
  return (
    <section id="features" className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            Everything you need to ship a production RAG pipeline
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6">
          {PILLARS.map((pillar) => (
            <Card key={pillar.title}>
              <h3 className="text-xl font-bold">{pillar.title}</h3>
              <p className="mt-3 text-[var(--color-muted)]">{pillar.description}</p>
              <div className="mt-6 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-4 py-3 font-mono text-sm overflow-x-auto">
                <span className="text-[var(--color-accent)]">$</span> {pillar.snippet}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
