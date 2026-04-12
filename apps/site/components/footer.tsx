import { SITE } from "@/lib/content";

const CURRENT_YEAR = new Date().getFullYear();

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] py-16">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          <div>
            <h4 className="font-mono text-sm font-bold text-[var(--color-foreground)]">
              Product
            </h4>
            <ul className="mt-4 space-y-2 text-sm text-[var(--color-muted)]">
              <li>
                <a href={SITE.github} className="hover:text-[var(--color-foreground)] transition-colors">
                  GitHub
                </a>
              </li>
              <li>
                <a href={SITE.npm} className="hover:text-[var(--color-foreground)] transition-colors">
                  npm
                </a>
              </li>
              <li>
                <a href={SITE.pypi} className="hover:text-[var(--color-foreground)] transition-colors">
                  PyPI
                </a>
              </li>
              <li>
                <a href={SITE.docs} className="hover:text-[var(--color-foreground)] transition-colors">
                  Documentation
                </a>
              </li>
              <li>
                <a href={SITE.contributing} className="hover:text-[var(--color-foreground)] transition-colors">
                  Contributing
                </a>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-mono text-sm font-bold text-[var(--color-foreground)]">
              Resources
            </h4>
            <ul className="mt-4 space-y-2 text-sm text-[var(--color-muted)]">
              <li>
                <a href="#rmm" className="hover:text-[var(--color-foreground)] transition-colors">
                  RAG Maturity Model
                </a>
              </li>
              <li>
                <a href="#templates" className="hover:text-[var(--color-foreground)] transition-colors">
                  Templates
                </a>
              </li>
              <li>
                <a href="#quick-start" className="hover:text-[var(--color-foreground)] transition-colors">
                  MCP Server
                </a>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-mono text-sm font-bold text-[var(--color-foreground)]">
              Project
            </h4>
            <ul className="mt-4 space-y-2 text-sm text-[var(--color-muted)]">
              <li>License: MIT</li>
              <li>Author: {SITE.author}</li>
              <li>© {CURRENT_YEAR}</li>
            </ul>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-[var(--color-border)] text-center text-xs font-mono text-[var(--color-muted)]">
          MIT licensed · © {CURRENT_YEAR} {SITE.author}
        </div>
      </div>
    </footer>
  );
}
