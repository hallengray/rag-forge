import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CopyButton } from "@/components/copy-button";
import { QUICK_START_DEV, QUICK_START_AGENT } from "@/lib/content";

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="relative rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] overflow-hidden">
      <div className="absolute top-3 right-3">
        <CopyButton value={code} />
      </div>
      <pre className="p-6 pr-14 overflow-x-auto font-mono text-sm leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function QuickStart() {
  return (
    <section id="quick-start" className="py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tighter">
            Get started in 60 seconds
          </h2>
        </div>

        <div className="mt-12 mx-auto max-w-3xl">
          <Tabs defaultValue="developers" className="w-full">
            <TabsList className="grid w-full grid-cols-2 max-w-sm mx-auto">
              <TabsTrigger value="developers">For developers</TabsTrigger>
              <TabsTrigger value="agents">For agents (MCP)</TabsTrigger>
            </TabsList>
            <TabsContent value="developers">
              <CodeBlock code={QUICK_START_DEV} />
            </TabsContent>
            <TabsContent value="agents">
              <CodeBlock code={QUICK_START_AGENT} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </section>
  );
}
