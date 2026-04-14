import { Check, Minus, X } from "lucide-react";
import { COMPARISON, COMPARISON_LAST_VERIFIED } from "@/lib/content";

function Cell({ value }: { value: boolean | "partial" }) {
  if (value === true) {
    return (
      <span className="inline-flex items-center justify-center">
        <Check className="h-5 w-5 text-[var(--color-accent)] mx-auto" aria-hidden="true" />
        <span className="sr-only">yes</span>
      </span>
    );
  }
  if (value === "partial") {
    return (
      <span className="inline-flex items-center justify-center">
        <Minus className="h-5 w-5 text-yellow-500 mx-auto" aria-hidden="true" />
        <span className="sr-only">partial</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center justify-center">
      <X
        className="h-5 w-5 text-[var(--color-muted)] mx-auto opacity-50"
        aria-hidden="true"
      />
      <span className="sr-only">no</span>
    </span>
  );
}

function formatLastVerified(value: string): string {
  const [year, month] = value.split("-");
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  const monthIndex = Number.parseInt(month ?? "", 10) - 1;
  const monthName = monthNames[monthIndex] ?? month;
  return `${monthName} ${year}`;
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
                <tr key={`${i}-${row}`} className="border-b border-[var(--color-border)]">
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
            Comparison based on publicly available features as of{" "}
            {formatLastVerified(COMPARISON_LAST_VERIFIED)}.
          </p>
        </div>

        <div className="mt-12 mx-auto max-w-3xl">
          <h3 className="text-sm font-semibold tracking-wide uppercase text-[var(--color-muted)] mb-4 text-center">
            Peer strengths worth knowing
          </h3>
          <ul className="space-y-3 text-sm text-[var(--color-muted)] leading-relaxed">
            {COMPARISON.peerStrengths.map((peer) => (
              <li key={peer.name}>
                <span className="font-semibold text-[var(--color-foreground)]">
                  {peer.name}:
                </span>{" "}
                {peer.detail}
              </li>
            ))}
          </ul>
          <p className="mt-6 text-xs text-[var(--color-muted)] text-center">
            Pick the tool that matches your stage. RAG-Forge&apos;s wedge is the
            full lifecycle — scaffold → evaluate → score → ship — in one CLI,
            with the RAG Maturity Model as the objective function.
          </p>
        </div>
      </div>
    </section>
  );
}
