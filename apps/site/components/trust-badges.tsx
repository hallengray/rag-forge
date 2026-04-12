import { Github, Package, Users } from "lucide-react";
import { TRUST } from "@/lib/content";

export function TrustBadges() {
  return (
    <section className="py-8 border-y border-[var(--color-border)]">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 font-mono text-sm text-[var(--color-muted)]">
          <div className="flex items-center gap-2">
            <Github className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.githubStars}</span>
            <span>stars</span>
          </div>
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.npmDownloads}</span>
            <span>npm/wk</span>
          </div>
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.pypiDownloads}</span>
            <span>PyPI/wk</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span className="text-[var(--color-foreground)] font-bold">{TRUST.contributors}</span>
            <span>contributors</span>
          </div>
        </div>
      </div>
    </section>
  );
}
