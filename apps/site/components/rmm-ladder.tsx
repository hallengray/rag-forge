import { cn } from "@/lib/utils";
import { RMM_LEVELS } from "@/lib/content";

export function RmmLadder() {
  return (
    <section id="rmm" className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            The RAG Maturity Model
          </h2>
          <p className="mt-6 text-lg text-[var(--color-muted)]">
            Where does your pipeline stand? Score any RAG system from RMM-0 (naive) to
            RMM-5 (enterprise).
          </p>
        </div>

        <div className="mt-16 mx-auto max-w-3xl">
          <div className="rounded-lg border border-[var(--color-accent)]/30 p-1 bg-gradient-to-br from-[var(--color-accent)]/10 to-transparent">
            <div className="rounded-md bg-[var(--color-background)] p-8">
              <ol className="space-y-4">
                {RMM_LEVELS.map((level) => (
                  <li
                    key={level.level}
                    className={cn(
                      "flex items-start gap-6 p-4 rounded-md transition-colors",
                      level.highlight &&
                        "bg-[var(--color-accent)]/5 border border-[var(--color-accent)]/30",
                    )}
                  >
                    <div
                      className={cn(
                        "flex-shrink-0 inline-flex items-center justify-center h-12 w-16 rounded-md font-mono font-bold border",
                        level.highlight
                          ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)] border-[var(--color-accent)]/30"
                          : "border-[var(--color-border)] text-[var(--color-muted)]",
                      )}
                    >
                      RMM-{level.level}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-bold">{level.name}</h3>
                        {level.highlight && (
                          <span className="text-xs font-mono text-[var(--color-accent)]">
                            ← Most pipelines stop here
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-[var(--color-muted)]">{level.description}</p>
                      <p className="mt-2 text-xs font-mono text-[var(--color-muted)]">
                        Gate: {level.criteria}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
