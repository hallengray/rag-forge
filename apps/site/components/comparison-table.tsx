import { Check, Minus, X } from "lucide-react";
import { COMPARISON } from "@/lib/content";

function Cell({ value }: { value: boolean | "partial" }) {
  if (value === true) {
    return <Check className="h-5 w-5 text-[var(--color-accent)] mx-auto" />;
  }
  if (value === "partial") {
    return <Minus className="h-5 w-5 text-yellow-500 mx-auto" />;
  }
  return <X className="h-5 w-5 text-[var(--color-muted)] mx-auto opacity-50" />;
}

export function ComparisonTable() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            How RAG-Forge compares
          </h2>
        </div>

        <div className="mt-12 mx-auto max-w-4xl overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="text-left py-4 px-4 font-medium text-[var(--color-muted)]">
                  Feature
                </th>
                <th className="py-4 px-4 font-mono font-bold text-[var(--color-accent)]">
                  rag-forge
                </th>
                <th className="py-4 px-4 font-mono text-[var(--color-muted)]">langchain</th>
                <th className="py-4 px-4 font-mono text-[var(--color-muted)]">llamaindex</th>
                <th className="py-4 px-4 font-mono text-[var(--color-muted)]">ragas</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.rows.map((row, i) => (
                <tr key={row} className="border-b border-[var(--color-border)]">
                  <td className="py-4 px-4">{row}</td>
                  <td className="py-4 px-4">
                    <Cell value={COMPARISON.values["rag-forge"][i]} />
                  </td>
                  <td className="py-4 px-4">
                    <Cell value={COMPARISON.values.langchain[i]} />
                  </td>
                  <td className="py-4 px-4">
                    <Cell value={COMPARISON.values.llamaindex[i]} />
                  </td>
                  <td className="py-4 px-4">
                    <Cell value={COMPARISON.values.ragas[i]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-6 text-xs text-[var(--color-muted)] font-mono text-center">
            Comparison based on publicly available features as of April 2026.
          </p>
        </div>
      </div>
    </section>
  );
}
