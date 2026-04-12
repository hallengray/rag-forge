import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CopyButton } from "@/components/copy-button";
import { TEMPLATES } from "@/lib/content";

export function Templates() {
  return (
    <section id="templates" className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            Start from a template
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {TEMPLATES.map((template) => {
            const command = `rag-forge init ${template.name}`;
            return (
              <Card key={template.name}>
                <div className="flex items-center justify-between">
                  <h3 className="font-mono text-lg font-bold">{template.name}</h3>
                  <Badge variant="outline">{template.complexity}</Badge>
                </div>
                <p className="mt-3 text-sm text-[var(--color-muted)]">
                  {template.description}
                </p>
                <div className="mt-4 flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 font-mono text-xs">
                  <span className="text-[var(--color-muted)]">$</span>
                  <span className="flex-1 truncate">{command}</span>
                  <CopyButton value={command} />
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
