# RAG-Forge Landing Page — Design Spec

**Date:** 2026-04-12
**Author:** Femi Adedayo (design), Claude (spec)
**Status:** Approved

## Overview

A static marketing landing page for RAG-Forge that explains the product, drives `npm install -g rag-forge` and GitHub stars, and serves as the destination URL for the npm/PyPI README links. Built with Next.js 16 App Router + Tailwind CSS v4 + shadcn/ui, deployed to Vercel as a static export.

## Goals

- Be the canonical "what is RAG-Forge?" URL
- Drive package installs and GitHub stars
- Convey credibility for the assessment consulting business (later)
- Ship in days, not weeks

## Non-Goals

- No backend, no auth, no database, no API routes
- No assessment booking flow (deferred to a later sub-project)
- No interactive RMM badge generator (deferred)
- No documentation site (deferred — link to README for now)
- No custom domain on day one (Vercel subdomain first, swap later)

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | Next.js 16 (App Router) |
| Rendering | Static export (`output: "export"`) |
| Styling | Tailwind CSS v4 |
| Components | shadcn/ui |
| Icons | lucide-react |
| Fonts | Geist Sans (headlines/body) + JetBrains Mono (code, badges) |
| Deployment | Vercel (auto-deploy on push to main, preview on PRs) |
| Initial URL | `rag-forge.vercel.app` |

## Repository Layout

The site lives in a new `apps/` workspace alongside the existing `packages/`. The Turborepo monorepo gets a new top-level workspace.

```text
RAGforge/
├── apps/
│   └── site/                    # Next.js 16 landing page
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx         # The single landing page
│       │   ├── globals.css      # Tailwind + theme variables
│       │   └── favicon.ico
│       ├── components/
│       │   ├── navbar.tsx
│       │   ├── hero.tsx
│       │   ├── trust-badges.tsx
│       │   ├── problem-section.tsx
│       │   ├── feature-grid.tsx
│       │   ├── rmm-ladder.tsx
│       │   ├── quick-start.tsx
│       │   ├── comparison-table.tsx
│       │   ├── templates.tsx
│       │   ├── footer.tsx
│       │   └── ui/              # shadcn/ui primitives (Button, Card, Badge, Tabs)
│       ├── lib/
│       │   ├── utils.ts         # cn() helper
│       │   └── content.ts       # All static content (headlines, copy, data)
│       ├── public/
│       │   └── og-image.png     # Open Graph image
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── package.json
│       └── components.json      # shadcn config
├── packages/                    # (unchanged)
├── pnpm-workspace.yaml          # Add "apps/*"
└── turbo.json                   # Already supports workspace tasks
```

## Page Sections

### 1. Sticky Navbar (`navbar.tsx`)

- Logo on the left: text wordmark "RAG-Forge" in JetBrains Mono with the bracket symbol `[ ]` as accent
- Center: anchor links (Features / RMM / Quick Start / Templates)
- Right: GitHub star count badge (read from a static value at build time, not live), Theme toggle, "Get Started" button (scrolls to Quick Start)
- Sticky on scroll, with backdrop blur

### 2. Hero (`hero.tsx`)

- **Headline (h1, tracking-tighter, 6xl-7xl):** "Production-grade RAG pipelines with evaluation baked in."
- **Subheadline (xl, muted):** "RAG-Forge bridges the gap between building RAG pipelines and knowing whether they actually work. Scaffold, evaluate, and assess any pipeline against the RAG Maturity Model."
- **Two CTAs:**
  - Primary: A click-to-copy button styled like a terminal command: `npx create-rag-forge@latest` (note: this is aspirational; actual command is `npm install -g rag-forge`. Use the install command for now since `create-rag-forge` doesn't exist yet)
  - Secondary: "View on GitHub →" linking to https://github.com/hallengray/rag-forge
- **Hero artifact (below CTAs):** A styled terminal screenshot rendered in JSX (not a real screenshot file). Mock the output of `rag-forge audit --golden-set qa.json` showing:
  - Green pass marks for some metrics (faithfulness 0.91, context relevance 0.84)
  - Red fail marks for others (recall@5 0.62)
  - An RMM-3 badge at the bottom
  - Fake colors via Tailwind classes; semantic structure so it's accessible
- Background: subtle dot grid pattern, no gradient blobs

### 3. Trust Badges (`trust-badges.tsx`)

A single inline row directly under the hero artifact:
- **GitHub:** stars (⭐ N)
- **npm:** weekly downloads
- **PyPI:** weekly downloads
- **Contributors:** count

All values are stored in `lib/content.ts` as constants and updated manually at release time. No live API calls (we're static-exported). Each badge is small monospace text with an icon.

### 4. The Problem (`problem-section.tsx`)

- Section header (h2): "The RAG quality crisis"
- One-paragraph intro
- Three stat cards (grid-cols-1 md:grid-cols-3):
  - **73%** — of enterprise RAG systems are over budget
  - **40%** — of RAG deployments lack systematic evaluation
  - **32%** — cite quality as the #1 deployment barrier
- Each card: large number in JetBrains Mono, short label, source citation in muted text

### 5. Four-Pillar Feature Grid (`feature-grid.tsx`)

- Section header (h2): "Everything you need to ship a production RAG pipeline"
- 2x2 grid (md:grid-cols-2):

  **Pillar 1 — Pipeline:**
  - Title: "Pipeline Primitives"
  - Description: "Five chunking strategies, dense + sparse + hybrid retrieval, contextual enrichment, and reranking. Bring your own embedding model."
  - Mini code snippet showing `create_chunker(ChunkConfig(strategy="semantic"))`

  **Pillar 2 — Evaluation:**
  - Title: "Evaluation as a CI/CD Gate"
  - Description: "RAGAS, DeepEval, and LLM-as-Judge baked in. Block PRs when faithfulness drops below threshold."
  - Mini code snippet showing `rag-forge audit --golden-set qa.json --threshold 0.85`

  **Pillar 3 — Observability:**
  - Title: "Built-in Observability"
  - Description: "OpenTelemetry tracing on every pipeline stage. Drift detection, cost estimation, semantic caching."
  - Mini code snippet showing `rag-forge drift report --baseline baseline.json`

  **Pillar 4 — Templates:**
  - Title: "Production Templates"
  - Description: "Five battle-tested starting points: basic, hybrid, agentic, enterprise, n8n. shadcn/ui model — you own every line of code."
  - Mini code snippet showing `rag-forge init enterprise`

### 6. The RMM Ladder (`rmm-ladder.tsx`) — The Standout Section

- Section header (h2): "The RAG Maturity Model"
- Subheadline: "Where does your pipeline stand? Score any RAG system from RMM-0 (naive) to RMM-5 (enterprise)."
- A vertical stepper with 6 rungs (RMM-0 through RMM-5):
  - Each rung: large level badge (e.g., "RMM-3"), level name, one-line description, gate criteria
  - Levels:
    - **RMM-0 Naive** — Basic vector search works
    - **RMM-1 Better Recall** — Hybrid search active, Recall@5 > 70%
    - **RMM-2 Better Precision** — Reranker active, nDCG@10 +10%
    - **RMM-3 Better Trust** — Guardrails, faithfulness > 85%, citations
    - **RMM-4 Better Workflow** — Caching, P95 < 4s, cost tracking
    - **RMM-5 Enterprise** — Drift detection, CI/CD gates, adversarial tests
  - Highlight RMM-3 with a green glow and "Most pipelines stop here" callout
- Wrapped in a gradient-bordered card to make it visually distinctive (Turborepo metric badge inspiration)
- Below the ladder: a CTA button "Score your pipeline" linking to the README assess docs

### 7. Quick Start (`quick-start.tsx`)

- Section header (h2): "Get started in 60 seconds"
- Tabbed code block with two tabs:
  - **Tab 1 — "For developers":**
    ```bash
    # Install the CLI
    npm install -g rag-forge

    # Scaffold a project
    rag-forge init basic

    # Index your docs and run an audit
    cd my-rag-project
    rag-forge index --source ./docs
    rag-forge audit --golden-set eval/golden_set.json
    ```
  - **Tab 2 — "For agents (MCP)":**
    ```bash
    # Run as an MCP server for Claude Code or any MCP client
    rag-forge serve --mcp --port 3100

    # Or via stdio for direct integration
    rag-forge serve --mcp --stdio
    ```
- Each command line has a copy-to-clipboard button on hover
- Code block uses JetBrains Mono with syntax highlighting via shiki or rehype-pretty-code

### 8. Comparison Table (`comparison-table.tsx`)

- Section header (h2): "How RAG-Forge compares"
- Table with 4 columns (RAG-Forge / LangChain / LlamaIndex / RAGAS) and these rows:
  - Framework agnostic (audit any pipeline)
  - Evaluation built in (CI/CD gate)
  - RAG Maturity Model scoring
  - OpenTelemetry native
  - MCP server
  - CLI scaffolding
  - Code ownership (shadcn model)
  - Drift detection
- Cells: green checkmark, gray dash, or red X
- Note below the table: "Comparison based on publicly available features as of April 2026."

### 9. Templates (`templates.tsx`)

- Section header (h2): "Start from a template"
- Five template cards in a grid:
  1. **basic** — First RAG project (Beginner)
  2. **hybrid** — Production-ready document Q&A (Intermediate)
  3. **agentic** — Multi-hop reasoning with query decomposition (Advanced)
  4. **enterprise** — Regulated industries with full security suite (Advanced)
  5. **n8n** — AI automation agency deployments (Intermediate)
- Each card: name (mono), one-line description, complexity badge, and the install command (`rag-forge init <name>`) with copy button

### 10. Footer (`footer.tsx`)

- Three-column grid:
  - **Column 1 — Product:** GitHub, npm, PyPI, Documentation (links to README), Contributing
  - **Column 2 — Resources:** RAG Maturity Model, Templates, MCP Server
  - **Column 3 — Project:** License (MIT), Author (Femi Adedayo), Copyright
- Bottom row: small monospace "MIT licensed · © 2026 Femi Adedayo"

## Theme & Styling

- **Dark mode default** with light mode toggle. Theme stored in `localStorage`, falls back to system preference.
- **Colors:**
  - Background dark: `#0a0a0a`
  - Background light: `#fafafa`
  - Foreground dark: `#fafafa`
  - Foreground light: `#0a0a0a`
  - Accent: **electric green** `#00d97e` (one accent color, used sparingly for CTAs, RMM badge highlight, "pass" indicators)
  - Muted: zinc-500
  - Border: zinc-800 (dark) / zinc-200 (light)
- **Typography:**
  - Headlines: Geist Sans, font-weight 600-700, tracking-tighter, sizes from 4xl to 7xl
  - Body: Geist Sans, font-weight 400, leading-relaxed
  - Code/badges/metrics: JetBrains Mono
- **Spacing:** Generous — `py-24` between sections on desktop, `py-16` on mobile. Max width `max-w-6xl`.

## Static Export Configuration

`next.config.ts`:
```ts
import type { NextConfig } from "next";

const config: NextConfig = {
  output: "export",
  images: {
    unoptimized: true, // required for static export
  },
  trailingSlash: false,
};

export default config;
```

`apps/site/package.json` scripts:
```json
{
  "build": "next build",
  "dev": "next dev",
  "lint": "eslint .",
  "typecheck": "tsc --noEmit"
}
```

## Turborepo Integration

`pnpm-workspace.yaml` — add `"apps/*"`:
```yaml
packages:
  - "packages/*"
  - "apps/*"
```

The existing `turbo.json` already orchestrates `build`, `lint`, `typecheck`, `test` for all workspaces. The site is picked up automatically.

## Vercel Deployment

- Connect the GitHub repo at https://vercel.com/new
- Select the `apps/site` directory as the root
- Vercel auto-detects Next.js + pnpm + Turborepo
- Build command: `cd ../.. && pnpm run build --filter=@rag-forge/site` (or use Vercel's monorepo support)
- Output directory: `apps/site/out` (Next.js static export)
- No environment variables needed (static site)
- Auto-deploy on push to `main`, preview on every PR

## Open Questions Resolved

- **OG image:** A simple text-on-dark `og-image.png` (1200x630) generated as part of the build (or hand-designed). Not blocking the launch.
- **Favicon:** Use the bracket `[ ]` symbol from the wordmark as a simple SVG favicon.
- **Analytics:** Vercel Web Analytics (free tier, privacy-friendly, no cookie banner needed).

## What's Required Before Launch

1. PR with the entire `apps/site/` directory
2. Update `pnpm-workspace.yaml` to include `apps/*`
3. Verify monorepo build still works (`pnpm run build`)
4. Connect Vercel to the repo
5. First deploy to `rag-forge.vercel.app`

## What's Deferred

- Custom domain (swap from `rag-forge.vercel.app` later)
- Documentation site (`apps/docs/`) — separate sub-project
- Assessment booking flow (`apps/portal/` or `/pricing` route) — separate sub-project
- Interactive RMM badge generator — separate sub-project
- Real GitHub star/download count via build-time fetch — manual constants for now

## Anti-Patterns Explicitly Avoided

- No Lottie/SVG flowing nodes hero animation (LangChain owns it)
- No vague verbs in headlines ("Empower," "Supercharge")
- No 9-icon feature grid (max 4 pillars)
- No fake testimonials or empty enterprise logo carousel
- No docs-as-landing-page (this is a marketing page, not a wiki)
- No light-mode-only or dark-mode-only (dev-tool table stakes is parity)
