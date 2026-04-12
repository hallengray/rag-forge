# RAG-Forge Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static Next.js 16 marketing landing page for RAG-Forge at `apps/site/`, deployed to Vercel as a static export.

**Architecture:** Add a new `apps/` workspace to the existing Turborepo monorepo. Build a single-page Next.js 16 App Router site with Tailwind CSS v4 + shadcn/ui, dark-mode default, electric green accent. Static export (`output: "export"`) so the entire site builds to plain HTML/CSS/JS — no server runtime. All content is hard-coded in `lib/content.ts`. The 10 page sections are split into 10 component files.

**Tech Stack:** Next.js 16 (App Router), Tailwind CSS v4, shadcn/ui, lucide-react, Geist Sans + JetBrains Mono, TypeScript strict mode, pnpm, Turborepo

**Branch:** `feat/landing-page`

---

## File Structure (Reference)

```
apps/
└── site/
    ├── app/
    │   ├── layout.tsx              # Root layout, fonts, theme provider
    │   ├── page.tsx                # The single landing page composing all sections
    │   ├── globals.css             # Tailwind directives + CSS variables
    │   └── favicon.ico
    ├── components/
    │   ├── navbar.tsx
    │   ├── hero.tsx
    │   ├── trust-badges.tsx
    │   ├── problem-section.tsx
    │   ├── feature-grid.tsx
    │   ├── rmm-ladder.tsx
    │   ├── quick-start.tsx
    │   ├── comparison-table.tsx
    │   ├── templates.tsx
    │   ├── footer.tsx
    │   ├── theme-provider.tsx     # Wraps next-themes
    │   ├── theme-toggle.tsx
    │   ├── copy-button.tsx        # Reusable click-to-copy
    │   └── ui/
    │       ├── button.tsx          # shadcn primitive
    │       ├── card.tsx            # shadcn primitive
    │       ├── badge.tsx           # shadcn primitive
    │       └── tabs.tsx            # shadcn primitive
    ├── lib/
    │   ├── utils.ts               # cn() helper from shadcn
    │   └── content.ts             # All static content as typed constants
    ├── public/
    │   └── (favicon assets)
    ├── next.config.ts
    ├── tailwind.config.ts          # Tailwind v4 uses CSS, but config file kept for plugin paths
    ├── postcss.config.mjs
    ├── tsconfig.json
    ├── package.json
    ├── components.json             # shadcn config
    ├── eslint.config.mjs
    └── README.md
```

---

### Task 1: Workspace Bootstrap

**Files:**
- Create: `apps/site/package.json`
- Create: `apps/site/tsconfig.json`
- Create: `apps/site/next.config.ts`
- Modify: `pnpm-workspace.yaml`
- Modify: `.gitignore` (add `apps/*/.next`, `apps/*/out`)

- [ ] **Step 1: Add `apps/*` to pnpm workspace**

Read `pnpm-workspace.yaml`. It currently has only `packages/*`. Add `apps/*`:

```yaml
packages:
  - "packages/*"
  - "apps/*"
```

- [ ] **Step 2: Create `apps/site/package.json`**

```json
{
  "name": "@rag-forge/site",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.1",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.468.0",
    "next": "^16.0.0",
    "next-themes": "^0.4.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tailwind-merge": "^2.5.5"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "autoprefixer": "^10.4.20",
    "eslint": "^9.0.0",
    "eslint-config-next": "^16.0.0",
    "postcss": "^8.5.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 3: Create `apps/site/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create `apps/site/next.config.ts`**

```ts
import type { NextConfig } from "next";

const config: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  trailingSlash: false,
};

export default config;
```

- [ ] **Step 5: Update `.gitignore`**

Append to existing `.gitignore`:

```
# Next.js
apps/*/.next
apps/*/out
apps/*/next-env.d.ts
```

- [ ] **Step 6: Install dependencies and verify**

```bash
cd "C:/Users/halle/Downloads/RAGforge"
pnpm install
ls apps/site/node_modules >/dev/null && echo "OK"
```

Expected: `OK` (or no error)

- [ ] **Step 7: Commit**

```bash
git add pnpm-workspace.yaml .gitignore apps/site/package.json apps/site/tsconfig.json apps/site/next.config.ts
git commit -m "feat(site): bootstrap apps/site Next.js workspace"
```

---

### Task 2: Tailwind v4 + Theme Setup

**Files:**
- Create: `apps/site/postcss.config.mjs`
- Create: `apps/site/tailwind.config.ts`
- Create: `apps/site/app/globals.css`

- [ ] **Step 1: Create PostCSS config**

`apps/site/postcss.config.mjs`:
```js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

Note: Tailwind v4 uses `@tailwindcss/postcss`. Add it to package.json devDeps:

Update `apps/site/package.json` devDependencies (run a quick edit):
```json
    "@tailwindcss/postcss": "^4.0.0",
```

Then re-run `pnpm install`.

- [ ] **Step 2: Create Tailwind config**

`apps/site/tailwind.config.ts`:
```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist-sans)"],
        mono: ["var(--font-geist-mono)"],
      },
      colors: {
        accent: {
          DEFAULT: "#00d97e",
          foreground: "#0a0a0a",
        },
      },
    },
  },
};

export default config;
```

- [ ] **Step 3: Create `apps/site/app/globals.css`**

```css
@import "tailwindcss";

@theme {
  --color-background: #0a0a0a;
  --color-foreground: #fafafa;
  --color-muted: #737373;
  --color-border: #262626;
  --color-card: #0f0f0f;
  --color-accent: #00d97e;
  --color-accent-foreground: #0a0a0a;
}

@theme inline {
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

:root {
  --color-background: #fafafa;
  --color-foreground: #0a0a0a;
  --color-muted: #737373;
  --color-border: #e5e5e5;
  --color-card: #ffffff;
}

.dark {
  --color-background: #0a0a0a;
  --color-foreground: #fafafa;
  --color-muted: #a3a3a3;
  --color-border: #262626;
  --color-card: #0f0f0f;
}

* {
  border-color: var(--color-border);
}

body {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-feature-settings: "rlig" 1, "calt" 1;
}

html {
  scroll-behavior: smooth;
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/site/postcss.config.mjs apps/site/tailwind.config.ts apps/site/app/globals.css apps/site/package.json
git commit -m "feat(site): add Tailwind v4 + theme tokens"
```

---

### Task 3: Root Layout + Theme Provider

**Files:**
- Create: `apps/site/components/theme-provider.tsx`
- Create: `apps/site/components/theme-toggle.tsx`
- Create: `apps/site/app/layout.tsx`
- Create: `apps/site/lib/utils.ts`

- [ ] **Step 1: Create `lib/utils.ts` (shadcn cn helper)**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create `components/theme-provider.tsx`**

```tsx
"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

- [ ] **Step 3: Create `components/theme-toggle.tsx`**

```tsx
"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-9 w-9" />;
  }

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--color-border)] hover:bg-[var(--color-card)] transition-colors"
      aria-label="Toggle theme"
    >
      {theme === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </button>
  );
}
```

- [ ] **Step 4: Create `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RAG-Forge — Production-grade RAG pipelines with evaluation baked in",
  description:
    "Framework-agnostic CLI toolkit that scaffolds production-grade RAG pipelines with evaluation baked in from day one. Score any RAG system against the RAG Maturity Model.",
  keywords: [
    "rag",
    "retrieval-augmented-generation",
    "evaluation",
    "llm",
    "rag-pipeline",
    "ragas",
  ],
  authors: [{ name: "Femi Adedayo" }],
  openGraph: {
    title: "RAG-Forge",
    description:
      "Production-grade RAG pipelines with evaluation baked in. Scaffold, evaluate, and assess any pipeline against the RAG Maturity Model.",
    url: "https://rag-forge.vercel.app",
    siteName: "RAG-Forge",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Verify dev server starts**

```bash
cd "C:/Users/halle/Downloads/RAGforge/apps/site"
pnpm run dev &
sleep 5
curl -sf http://localhost:3000 >/dev/null && echo "OK" || echo "FAIL"
kill %1 2>/dev/null || true
```

Expected: `OK`. Note: The page won't render anything yet (no `page.tsx`), but the dev server should boot without errors.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/halle/Downloads/RAGforge"
git add apps/site/lib/utils.ts apps/site/components/theme-provider.tsx apps/site/components/theme-toggle.tsx apps/site/app/layout.tsx
git commit -m "feat(site): add root layout with theme provider"
```

---

### Task 4: shadcn/ui Primitives

**Files:**
- Create: `apps/site/components.json`
- Create: `apps/site/components/ui/button.tsx`
- Create: `apps/site/components/ui/card.tsx`
- Create: `apps/site/components/ui/badge.tsx`
- Create: `apps/site/components/ui/tabs.tsx`

- [ ] **Step 1: Create shadcn config**

`apps/site/components.json`:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 2: Create `components/ui/button.tsx`**

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--color-accent)] text-[var(--color-accent-foreground)] hover:bg-[var(--color-accent)]/90",
        outline:
          "border border-[var(--color-border)] bg-transparent hover:bg-[var(--color-card)]",
        ghost: "hover:bg-[var(--color-card)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3",
        lg: "h-11 px-8 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

- [ ] **Step 3: Create `components/ui/card.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

export { Card };
```

- [ ] **Step 4: Create `components/ui/badge.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "outline" | "accent";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-[var(--color-card)] text-[var(--color-foreground)]",
    outline: "border border-[var(--color-border)] bg-transparent",
    accent:
      "bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium font-mono",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
```

- [ ] **Step 5: Create `components/ui/tabs.tsx`**

```tsx
"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-10 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-1",
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all data-[state=active]:bg-[var(--color-background)] data-[state=active]:text-[var(--color-foreground)] data-[state=inactive]:text-[var(--color-muted)]",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-4 focus-visible:outline-none", className)}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
```

- [ ] **Step 6: Commit**

```bash
git add apps/site/components.json apps/site/components/ui/
git commit -m "feat(site): add shadcn/ui primitives (Button, Card, Badge, Tabs)"
```

---

### Task 5: Static Content + Copy Button Helper

**Files:**
- Create: `apps/site/lib/content.ts`
- Create: `apps/site/components/copy-button.tsx`

- [ ] **Step 1: Create `lib/content.ts` with all static content**

```ts
export const SITE = {
  name: "RAG-Forge",
  url: "https://rag-forge.vercel.app",
  github: "https://github.com/hallengray/rag-forge",
  npm: "https://www.npmjs.com/package/rag-forge",
  pypi: "https://pypi.org/project/rag-forge-core",
  docs: "https://github.com/hallengray/rag-forge#readme",
  contributing:
    "https://github.com/hallengray/rag-forge/blob/main/CONTRIBUTING.md",
  author: "Femi Adedayo",
} as const;

export const TRUST = {
  githubStars: "120",
  npmDownloads: "1.2k",
  pypiDownloads: "850",
  contributors: "8",
} as const;

export const HERO = {
  headline: "Production-grade RAG pipelines with evaluation baked in.",
  subheadline:
    "RAG-Forge bridges the gap between building RAG pipelines and knowing whether they actually work. Scaffold, evaluate, and assess any pipeline against the RAG Maturity Model.",
  installCommand: "npm install -g rag-forge",
} as const;

export const PROBLEMS = [
  {
    stat: "73%",
    label: "of enterprise RAG systems are over budget",
    source: "Industry analysis, 2026",
  },
  {
    stat: "40%",
    label: "of RAG deployments lack systematic evaluation",
    source: "Industry surveys, early 2026",
  },
  {
    stat: "32%",
    label: "cite quality as the #1 deployment barrier",
    source: "LangChain State of AI Agents 2026",
  },
] as const;

export const PILLARS = [
  {
    title: "Pipeline Primitives",
    description:
      "Five chunking strategies, dense + sparse + hybrid retrieval, contextual enrichment, and reranking. Bring your own embedding model.",
    snippet: "create_chunker(ChunkConfig(strategy=\"semantic\"))",
  },
  {
    title: "Evaluation as a CI/CD Gate",
    description:
      "RAGAS, DeepEval, and LLM-as-Judge baked in. Block PRs when faithfulness drops below threshold.",
    snippet: "rag-forge audit --golden-set qa.json --threshold 0.85",
  },
  {
    title: "Built-in Observability",
    description:
      "OpenTelemetry tracing on every pipeline stage. Drift detection, cost estimation, semantic caching.",
    snippet: "rag-forge drift report --baseline baseline.json",
  },
  {
    title: "Production Templates",
    description:
      "Five battle-tested starting points. shadcn/ui model — you own every line of code.",
    snippet: "rag-forge init enterprise",
  },
] as const;

export const RMM_LEVELS = [
  {
    level: 0,
    name: "Naive",
    description: "Basic vector search works",
    criteria: "Vector retrieval returns results",
  },
  {
    level: 1,
    name: "Better Recall",
    description: "Hybrid search active, Recall@5 > 70%",
    criteria: "Dense + sparse + RRF fusion",
  },
  {
    level: 2,
    name: "Better Precision",
    description: "Reranker active, nDCG@10 +10%",
    criteria: "Cross-encoder reranking on top results",
  },
  {
    level: 3,
    name: "Better Trust",
    description: "Guardrails, faithfulness > 85%, citations",
    criteria: "InputGuard + OutputGuard active",
    highlight: true,
  },
  {
    level: 4,
    name: "Better Workflow",
    description: "Caching, P95 < 4s, cost tracking",
    criteria: "Semantic cache + telemetry + cost meter",
  },
  {
    level: 5,
    name: "Enterprise",
    description: "Drift detection, CI/CD gates, adversarial tests",
    criteria: "All audit thresholds pass",
  },
] as const;

export const QUICK_START_DEV = `# Install the CLI
npm install -g rag-forge

# Scaffold a project
rag-forge init basic

# Index your docs and run an audit
cd my-rag-project
rag-forge index --source ./docs
rag-forge audit --golden-set eval/golden_set.json`;

export const QUICK_START_AGENT = `# Run as an MCP server for Claude Code or any MCP client
rag-forge serve --mcp --port 3100

# Or via stdio for direct integration
rag-forge serve --mcp --stdio`;

export const COMPARISON = {
  rows: [
    "Framework agnostic (audit any pipeline)",
    "Evaluation built in (CI/CD gate)",
    "RAG Maturity Model scoring",
    "OpenTelemetry native",
    "MCP server",
    "CLI scaffolding",
    "Code ownership (shadcn model)",
    "Drift detection",
  ],
  values: {
    "rag-forge": [true, true, true, true, true, true, true, true],
    langchain: [false, "partial", false, "partial", false, false, false, false],
    llamaindex: [false, false, false, false, false, false, false, false],
    ragas: [true, true, false, false, false, false, false, false],
  },
} as const;

export const TEMPLATES = [
  {
    name: "basic",
    description: "First RAG project, simple Q&A",
    complexity: "Beginner",
  },
  {
    name: "hybrid",
    description: "Production-ready document Q&A with reranking",
    complexity: "Intermediate",
  },
  {
    name: "agentic",
    description: "Multi-hop reasoning with query decomposition",
    complexity: "Advanced",
  },
  {
    name: "enterprise",
    description: "Regulated industries with full security suite",
    complexity: "Advanced",
  },
  {
    name: "n8n",
    description: "AI automation agency deployments",
    complexity: "Intermediate",
  },
] as const;
```

- [ ] **Step 2: Create `components/copy-button.tsx`**

```tsx
"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface CopyButtonProps {
  value: string;
  className?: string;
}

export function CopyButton({ value, className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-border)] hover:bg-[var(--color-card)] transition-colors",
        className,
      )}
      aria-label="Copy to clipboard"
    >
      {copied ? (
        <Check className="h-4 w-4 text-[var(--color-accent)]" />
      ) : (
        <Copy className="h-4 w-4" />
      )}
    </button>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/site/lib/content.ts apps/site/components/copy-button.tsx
git commit -m "feat(site): add static content and copy button helper"
```

---

### Task 6: Navbar

**Files:**
- Create: `apps/site/components/navbar.tsx`

- [ ] **Step 1: Create the navbar**

```tsx
import Link from "next/link";
import { Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { SITE, TRUST } from "@/lib/content";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur supports-[backdrop-filter]:bg-[var(--color-background)]/80 border-b border-[var(--color-border)]">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="font-mono text-lg font-bold">
          <span className="text-[var(--color-accent)]">[</span>
          {" "}rag-forge{" "}
          <span className="text-[var(--color-accent)]">]</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm text-[var(--color-muted)]">
          <Link href="#features" className="hover:text-[var(--color-foreground)] transition-colors">
            Features
          </Link>
          <Link href="#rmm" className="hover:text-[var(--color-foreground)] transition-colors">
            RMM
          </Link>
          <Link href="#quick-start" className="hover:text-[var(--color-foreground)] transition-colors">
            Quick Start
          </Link>
          <Link href="#templates" className="hover:text-[var(--color-foreground)] transition-colors">
            Templates
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={SITE.github}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-2 px-3 h-9 rounded-md border border-[var(--color-border)] hover:bg-[var(--color-card)] text-sm font-mono"
          >
            <Github className="h-4 w-4" />
            <span>{TRUST.githubStars}</span>
          </a>
          <ThemeToggle />
          <Button size="sm" asChild>
            <Link href="#quick-start">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/navbar.tsx
git commit -m "feat(site): add sticky navbar"
```

---

### Task 7: Hero Section

**Files:**
- Create: `apps/site/components/hero.tsx`

- [ ] **Step 1: Create the hero**

```tsx
import { ArrowRight, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/copy-button";
import { HERO, SITE } from "@/lib/content";

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-20 pb-24 sm:pt-32 sm:pb-32">
      {/* Subtle dot grid background */}
      <div
        className="absolute inset-0 -z-10 opacity-[0.15]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, var(--color-foreground) 1px, transparent 0)",
          backgroundSize: "32px 32px",
        }}
      />

      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tighter leading-[1.05]">
            {HERO.headline}
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-[var(--color-muted)] leading-relaxed max-w-3xl mx-auto">
            {HERO.subheadline}
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] font-mono text-sm">
              <span className="text-[var(--color-muted)]">$</span>
              <span>{HERO.installCommand}</span>
              <CopyButton value={HERO.installCommand} className="ml-2" />
            </div>
            <Button variant="outline" size="lg" asChild>
              <a href={SITE.github} target="_blank" rel="noopener noreferrer">
                <Github className="h-4 w-4" />
                View on GitHub
                <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>

        {/* Hero artifact: terminal mock */}
        <div className="mt-16 mx-auto max-w-4xl">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] overflow-hidden shadow-2xl">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-background)]">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-500/60" />
                <div className="h-3 w-3 rounded-full bg-yellow-500/60" />
                <div className="h-3 w-3 rounded-full bg-green-500/60" />
              </div>
              <span className="text-xs font-mono text-[var(--color-muted)] ml-2">rag-forge audit</span>
            </div>
            <div className="p-6 font-mono text-sm space-y-2">
              <div className="text-[var(--color-muted)]">$ rag-forge audit --golden-set qa.json</div>
              <div className="text-[var(--color-muted)]">Running RAGAS evaluation on 50 samples...</div>
              <div className="mt-4 space-y-1">
                <div className="flex justify-between">
                  <span>faithfulness</span>
                  <span className="text-[var(--color-accent)]">0.91 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>context_relevance</span>
                  <span className="text-[var(--color-accent)]">0.84 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>answer_relevance</span>
                  <span className="text-[var(--color-accent)]">0.88 PASS</span>
                </div>
                <div className="flex justify-between">
                  <span>recall_at_k</span>
                  <span className="text-red-400">0.62 FAIL</span>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/30">
                    RMM-3
                  </span>
                  <span className="text-[var(--color-muted)]">Better Trust</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/hero.tsx
git commit -m "feat(site): add hero section with terminal mock"
```

---

### Task 8: Trust Badges

**Files:**
- Create: `apps/site/components/trust-badges.tsx`

- [ ] **Step 1: Create trust badges**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/trust-badges.tsx
git commit -m "feat(site): add trust badges row"
```

---

### Task 9: Problem Section

**Files:**
- Create: `apps/site/components/problem-section.tsx`

- [ ] **Step 1: Create the problem section**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/problem-section.tsx
git commit -m "feat(site): add problem section with stat cards"
```

---

### Task 10: Feature Grid

**Files:**
- Create: `apps/site/components/feature-grid.tsx`

- [ ] **Step 1: Create the feature grid**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/feature-grid.tsx
git commit -m "feat(site): add four-pillar feature grid"
```

---

### Task 11: RMM Ladder

**Files:**
- Create: `apps/site/components/rmm-ladder.tsx`

- [ ] **Step 1: Create the RMM ladder**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/rmm-ladder.tsx
git commit -m "feat(site): add RMM ladder with gradient-bordered card"
```

---

### Task 12: Quick Start (Tabbed)

**Files:**
- Create: `apps/site/components/quick-start.tsx`

- [ ] **Step 1: Create quick start**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/quick-start.tsx
git commit -m "feat(site): add tabbed quick start section"
```

---

### Task 13: Comparison Table

**Files:**
- Create: `apps/site/components/comparison-table.tsx`

- [ ] **Step 1: Create comparison table**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/comparison-table.tsx
git commit -m "feat(site): add comparison table vs LangChain/LlamaIndex/RAGAS"
```

---

### Task 14: Templates Section

**Files:**
- Create: `apps/site/components/templates.tsx`

- [ ] **Step 1: Create templates**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/templates.tsx
git commit -m "feat(site): add templates section"
```

---

### Task 15: Footer

**Files:**
- Create: `apps/site/components/footer.tsx`

- [ ] **Step 1: Create footer**

```tsx
import { SITE } from "@/lib/content";

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
              <li>© 2026</li>
            </ul>
          </div>
        </div>
        <div className="mt-12 pt-8 border-t border-[var(--color-border)] text-center text-xs font-mono text-[var(--color-muted)]">
          MIT licensed · © 2026 {SITE.author}
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/site/components/footer.tsx
git commit -m "feat(site): add footer"
```

---

### Task 16: Compose Page + Build Verification

**Files:**
- Create: `apps/site/app/page.tsx`
- Create: `apps/site/eslint.config.mjs`
- Create: `apps/site/README.md`

- [ ] **Step 1: Create the composed page**

```tsx
import { Navbar } from "@/components/navbar";
import { Hero } from "@/components/hero";
import { TrustBadges } from "@/components/trust-badges";
import { ProblemSection } from "@/components/problem-section";
import { FeatureGrid } from "@/components/feature-grid";
import { RmmLadder } from "@/components/rmm-ladder";
import { QuickStart } from "@/components/quick-start";
import { ComparisonTable } from "@/components/comparison-table";
import { Templates } from "@/components/templates";
import { Footer } from "@/components/footer";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <TrustBadges />
        <ProblemSection />
        <FeatureGrid />
        <RmmLadder />
        <QuickStart />
        <ComparisonTable />
        <Templates />
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 2: Create ESLint config**

`apps/site/eslint.config.mjs`:
```js
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
```

Add `@eslint/eslintrc` to devDependencies:
```bash
cd "C:/Users/halle/Downloads/RAGforge/apps/site"
pnpm add -D @eslint/eslintrc
cd ../..
```

- [ ] **Step 3: Create site README**

`apps/site/README.md`:
```markdown
# @rag-forge/site

The marketing landing page for RAG-Forge. Built with Next.js 16, Tailwind CSS v4, and shadcn/ui. Static export, deployed to Vercel.

## Development

```bash
pnpm install
pnpm --filter @rag-forge/site dev
```

Open http://localhost:3000

## Build

```bash
pnpm --filter @rag-forge/site build
```

Output: `apps/site/out/`

## Deployment

Auto-deployed to Vercel on push to `main`. Preview deployments on every PR.
```

- [ ] **Step 4: Run typecheck, lint, and build**

```bash
cd "C:/Users/halle/Downloads/RAGforge"
pnpm install
pnpm --filter @rag-forge/site typecheck
pnpm --filter @rag-forge/site lint
pnpm --filter @rag-forge/site build
```

Expected: All three succeed. Build output appears in `apps/site/out/`.

- [ ] **Step 5: Verify build output**

```bash
ls apps/site/out/index.html && echo "OK"
```

Expected: `apps/site/out/index.html` exists, prints `OK`.

- [ ] **Step 6: Commit**

```bash
git add apps/site/app/page.tsx apps/site/eslint.config.mjs apps/site/README.md apps/site/package.json
git commit -m "feat(site): compose landing page and verify static export build"
```

---

### Task 17: Push and Open PR

- [ ] **Step 1: Run full monorepo build to ensure nothing is broken**

```bash
cd "C:/Users/halle/Downloads/RAGforge"
pnpm run build
```

Expected: All workspaces (cli, mcp, shared, site) build successfully.

- [ ] **Step 2: Push and create PR**

```bash
git push -u origin feat/landing-page
gh pr create --title "feat(site): add Next.js 16 landing page at apps/site" --body "$(cat <<'EOF'
## Summary
- Adds new \`apps/\` workspace to the monorepo with a Next.js 16 landing page
- Static export deployment ready (no server runtime, no API routes)
- 10 sections: hero with terminal mock, trust badges, problem stats, four-pillar feature grid, RMM ladder, tabbed quick start, comparison table, templates, footer, sticky navbar
- Dark mode default with light mode toggle, electric green accent, Geist + JetBrains Mono fonts
- Designed to be the canonical \"what is RAG-Forge?\" URL referenced from npm/PyPI/GitHub

## Tech Stack
- Next.js 16 (App Router)
- Tailwind CSS v4
- shadcn/ui (Button, Card, Badge, Tabs)
- next-themes (dark mode)
- lucide-react (icons)

## Test plan
- [x] \`pnpm --filter @rag-forge/site typecheck\` zero errors
- [x] \`pnpm --filter @rag-forge/site lint\` zero errors
- [x] \`pnpm --filter @rag-forge/site build\` produces \`apps/site/out/index.html\`
- [x] \`pnpm run build\` (full monorepo) succeeds

## Deployment Setup (manual, after merge)
1. Connect the GitHub repo to Vercel
2. Select \`apps/site\` as the root directory
3. Vercel auto-detects Next.js + pnpm + Turborepo
4. Deploy → \`rag-forge.vercel.app\`

## What's Deferred
- Custom domain (swap from Vercel subdomain later)
- Real GitHub stars/download counts via build-time fetch (manual constants for now in \`lib/content.ts\`)
- Documentation site (separate sub-project)
- Assessment booking flow (separate sub-project)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
