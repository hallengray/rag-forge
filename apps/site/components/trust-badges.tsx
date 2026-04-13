import { Sparkles, Shield, ShieldCheck, Rocket } from "lucide-react";
import { TRUST } from "@/lib/content";

export function TrustBadges() {
  return (
    <section className="py-8 border-y border-[var(--color-border)]">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 font-mono text-sm text-[var(--color-muted)]">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.status}</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.license}</span>
            <span>licensed</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.publishedVia}</span>
          </div>
          <div className="flex items-center gap-2">
            <Rocket className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.earlyAdopter}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
