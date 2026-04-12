# RAG-Forge Documentation Site — Design Spec

**Date:** 2026-04-12
**Author:** Femi Adedayo (design), Claude (spec)
**Status:** Approved

## Overview

A documentation site for RAG-Forge built with Next.js 16 + Nextra v4, deployed to Vercel as a separate project from the landing page. Wraps existing markdown content (PRD sections, READMEs, command help text, design specs) into a navigable, searchable site with a sidebar nav, full-text search, and visual identity that matches the landing page.

## Goals

- Provide a single canonical URL for "how do I use RAG-Forge?" content
- Wrap and surface existing content rather than duplicate it
- Match the landing page visual identity (dark mode default, electric green accent, Geist + JetBrains Mono)
- Be searchable with zero infrastructure cost
- Ship in days, not weeks

## Non-Goals

- No content management system or web-based editor
- No user accounts, auth, comments, or feedback widgets
- No versioned docs at launch (defer to v0.2)
- No API reference auto-generation from code (manual CLI reference for now)
- No translations
- No custom domain at launch (Vercel subdomain first)
- No backend, no database
- No Algolia DocSearch (use Nextra's built-in client-side search)

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | Next.js 16 (App Router) |
| Docs theme | `nextra` v4 + `nextra-theme-docs` |
| Content format | MDX |
| Search | Nextra built-in (FlexSearch, client-side, build-time index) |
| Styling | Nextra defaults + CSS variable overrides matching landing page |
| Fonts | Geist Sans (body, headings) + JetBrains Mono (code) |
| Deployment | Vercel, separate project from landing page |
| Initial URL | `rag-forge-docs.vercel.app` |

## Repository Layout

The docs site lives in a new `apps/docs/` workspace alongside `apps/site/`. The Turborepo `apps/*` workspace pattern is already established by PR #18.

```text
apps/
├── site/                       # Existing — landing page
└── docs/                       # New — Nextra docs site
    ├── app/
    │   ├── layout.tsx          # Root layout, fonts, Nextra wrapper
    │   ├── [[...mdxPath]]/
    │   │   └── page.jsx        # Nextra catch-all route
    │   └── globals.css         # Theme variable overrides
    ├── content/                # All MDX content
    │   ├── _meta.json          # Top-level nav
    │   ├── index.mdx           # Home (welcome page)
    │   ├── getting-started/
    │   │   ├── _meta.json
    │   │   ├── installation.mdx
    │   │   ├── quick-start.mdx
    │   │   └── concepts.mdx
    │   ├── cli/
    │   │   ├── _meta.json
    │   │   ├── overview.mdx
    │   │   ├── init.mdx
    │   │   ├── add.mdx
    │   │   ├── parse.mdx
    │   │   ├── chunk.mdx
    │   │   ├── index-command.mdx  # rag-forge index command (filename avoids collision with Nextra's /cli/index route)
    │   │   ├── query.mdx
    │   │   ├── inspect.mdx
    │   │   ├── audit.mdx
    │   │   ├── assess.mdx
    │   │   ├── golden.mdx      # golden add + golden validate
    │   │   ├── drift.mdx       # drift report + drift save-baseline
    │   │   ├── cost.mdx
    │   │   ├── guardrails.mdx  # guardrails test + guardrails scan-pii
    │   │   ├── report.mdx
    │   │   ├── cache.mdx       # cache stats
    │   │   ├── serve.mdx       # serve --mcp
    │   │   └── n8n.mdx         # n8n export
    │   ├── templates/
    │   │   ├── _meta.json
    │   │   ├── basic.mdx
    │   │   ├── hybrid.mdx
    │   │   ├── agentic.mdx
    │   │   ├── enterprise.mdx
    │   │   └── n8n.mdx
    │   ├── concepts/
    │   │   ├── _meta.json
    │   │   ├── rmm.mdx
    │   │   ├── chunking.mdx
    │   │   ├── retrieval.mdx
    │   │   ├── evaluation.mdx
    │   │   └── observability.mdx
    │   ├── mcp/
    │   │   ├── _meta.json
    │   │   └── overview.mdx
    │   └── contributing.mdx
    ├── theme.config.tsx
    ├── mdx-components.tsx      # Nextra MDX component overrides
    ├── next.config.ts
    ├── tsconfig.json
    ├── package.json
    └── README.md
```

## Page Inventory (Initial Release)

**Total: 34 pages** (1 home + 3 getting started + 18 CLI reference + 5 templates + 5 concepts + 1 MCP + 1 contributing)

### Section 1: Getting Started (3 pages)

1. `getting-started/installation.mdx`
2. `getting-started/quick-start.mdx`
3. `getting-started/concepts.mdx`

### Section 2: CLI Reference (18 pages)

1. `cli/overview.mdx` — All commands at a glance
2. `cli/init.mdx`
3. `cli/add.mdx`
4. `cli/parse.mdx`
5. `cli/chunk.mdx`
6. `cli/index.mdx` — `rag-forge index` (the file is named `index.mdx`, but Nextra renders it as `/cli/index` not the section index — note: rename to avoid collision; actual filename will be `cli/index-command.mdx` with display name "index" via `_meta.json`)
7. `cli/query.mdx`
8. `cli/inspect.mdx`
9. `cli/audit.mdx`
10. `cli/assess.mdx`
11. `cli/golden.mdx`
12. `cli/drift.mdx`
13. `cli/cost.mdx`
14. `cli/guardrails.mdx`
15. `cli/report.mdx`
16. `cli/cache.mdx`
17. `cli/serve.mdx`
18. `cli/n8n.mdx`

### Section 3: Templates (5 pages)

1. `templates/basic.mdx`
2. `templates/hybrid.mdx`
3. `templates/agentic.mdx`
4. `templates/enterprise.mdx`
5. `templates/n8n.mdx`

### Section 4: Concepts (5 pages)

1. `concepts/rmm.mdx` — RAG Maturity Model
2. `concepts/chunking.mdx`
3. `concepts/retrieval.mdx`
4. `concepts/evaluation.mdx`
5. `concepts/observability.mdx`

### Section 5: MCP (1 page)

1. `mcp/overview.mdx`

### Section 6: Contributing (1 page)

1. `contributing.mdx` — Condensed version + link to root `CONTRIBUTING.md`

### Home (1 page)

1. `index.mdx` — Welcome landing page with quick links to each section

## Page Template Standards

### CLI Reference Pages

Every CLI page follows this template:

```mdx
# rag-forge {command}

> One-line description of what the command does.

## Synopsis

\`\`\`bash
rag-forge {command} [options]
\`\`\`

## Description

1-2 paragraphs explaining what the command does, when to use it, and what to expect.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--flag1` | — | What it does |
| `--flag2 <value>` | `default` | What it does |

## Examples

### Basic usage

\`\`\`bash
rag-forge {command} --flag1
\`\`\`

Expected output:

\`\`\`
... output ...
\`\`\`

### Advanced usage

(another example)

## Related commands

- [`rag-forge other-command`](/cli/other-command)
```

### Concept Pages

```mdx
# Concept Name

> One-paragraph plain-English summary.

## Why this matters

Background and motivation. Reference real numbers from PRD.

## How RAG-Forge implements it

Concrete details about the implementation, file paths in `packages/core/`, and which CLI commands surface this concept.

## Trade-offs

When to use this, when not to.

## Further reading

Links to external resources, papers, or related concepts in the docs.
```

### Template Pages

```mdx
# {template} template

> What it builds and who it's for.

## What you get

File tree of the generated project.

## Default configuration

The starting config in `rag-forge.config.ts`.

## Recommended next steps

1. Step one
2. Step two
3. Step three

## When to upgrade

When to switch from this template to a more advanced one.
```

## Content Sourcing Map

| Docs page | Source |
|-----------|--------|
| Installation | Root `README.md` (after PR #17 merges) |
| Quick Start | Root `README.md` + landing page Quick Start section |
| CLI commands | `--help` output of each command + PRD Section 7 |
| Templates | `templates/<name>/README.md` (if exists) + the template's `pyproject.toml`/`package.json` |
| RMM concepts | `packages/evaluator/src/rag_forge_evaluator/maturity.py` + PRD Section 8 |
| Chunking concepts | PRD Section 6.1 + `packages/core/src/rag_forge_core/chunking/` |
| Retrieval concepts | PRD Section 6.3 + `packages/core/src/rag_forge_core/retrieval/` |
| Evaluation concepts | PRD Section 6.4 + `packages/evaluator/src/rag_forge_evaluator/` |
| Observability concepts | PRD Section 6.7 + `packages/observability/src/` |
| MCP overview | PRD Section 6.6 + `packages/mcp/src/index.ts` |
| Contributing | Existing `CONTRIBUTING.md` |

## Theme Configuration

`apps/docs/theme.config.tsx` defines:

- **Logo:** Mono wordmark `[ rag-forge ]` matching the landing page navbar
- **Project link:** GitHub URL
- **Chat link:** None (no Discord or Slack yet)
- **Docs repository:** Points at `https://github.com/hallengray/rag-forge/tree/main/apps/docs/content` for "Edit this page on GitHub" links
- **Sidebar:** Default expanded, collapsible groups
- **Footer:** Mono "MIT licensed · © 2026 Femi Adedayo"
- **Search:** Enabled (Nextra's built-in)
- **Color mode:** Default to dark
- **Primary hue:** Override Nextra's default primary color to match electric green `#00d97e`

`apps/docs/app/globals.css` overrides Nextra theme variables:

```css
@import "nextra-theme-docs/style.css";

:root {
  --nextra-primary-hue: 152;     /* Green-tinted */
  --nextra-primary-saturation: 100%;
  --nextra-primary-lightness: 42%;
}

html.dark {
  --nextra-bg: #0a0a0a;
  --nextra-fg: #fafafa;
}

html.light {
  --nextra-bg: #fafafa;
  --nextra-fg: #0a0a0a;
}
```

## Nextra Configuration

`apps/docs/next.config.ts`:

```ts
import nextra from "nextra";

const withNextra = nextra({
  search: {
    codeblocks: true,
  },
  defaultShowCopyCode: true,
});

export default withNextra({
  reactStrictMode: true,
});
```

`apps/docs/mdx-components.tsx`:

```ts
import { useMDXComponents as getThemeComponents } from "nextra-theme-docs";

const themeComponents = getThemeComponents();

export function useMDXComponents(components?: Record<string, React.ComponentType>) {
  return {
    ...themeComponents,
    ...components,
  };
}
```

## Sidebar Configuration (`_meta.json` files)

Top-level `apps/docs/content/_meta.json`:

```json
{
  "index": "Home",
  "getting-started": "Getting Started",
  "cli": "CLI Reference",
  "templates": "Templates",
  "concepts": "Concepts",
  "mcp": "MCP Server",
  "contributing": "Contributing"
}
```

Each section has its own `_meta.json` defining the order and display names of pages within that section.

## Vercel Deployment

- **Project name on Vercel:** `rag-forge-docs`
- **GitHub repo:** `hallengray/rag-forge` (same as landing page)
- **Root directory:** `apps/docs`
- **Framework preset:** Next.js (auto-detected)
- **Build command:** `cd ../.. && pnpm run build --filter @rag-forge/docs`
- **Output directory:** Default (Next.js standalone build)
- **Install command:** `cd ../.. && pnpm install --no-frozen-lockfile`
- **Initial URL:** `rag-forge-docs.vercel.app`
- **Auto-deploy on push to main, preview on every PR**

## What's Required Before Launch

1. PR with `apps/docs/` directory and all 34 MDX pages
2. Verify the full monorepo build still works (`pnpm run build`)
3. Connect Vercel to the repo as a new project (separate from landing page)
4. First deploy to `rag-forge-docs.vercel.app`

## What's Deferred

- Custom domain (`docs.rag-forge.dev`) — swap from Vercel subdomain later
- Versioned docs — defer until v0.2 ships
- API reference auto-generation from Python type hints
- Algolia DocSearch
- Translations
- Edit-on-GitHub button (added in `theme.config.tsx` but won't work until repo is public-friendly)

## Anti-Patterns Explicitly Avoided

- No empty placeholder pages or "Coming Soon" navigation entries
- No content duplication — link to canonical sources where they exist
- No mismatch with landing page visual identity
- No static export hacks that fight Nextra (run as a normal Next.js server-rendered app)
- No CMS, no auth, no backend
- No fake screenshots or placeholder images

## Content Writing Workload Estimate

Of the 34 pages, here's where the prose actually has to be written:

| Source | Pages | Effort |
|--------|-------|--------|
| Pure extraction (CLI, templates) | 23 | Mostly mechanical — copy and reformat |
| Light prose (Home, Getting Started, MCP, Contributing) | 6 | ~200 words each = 1,200 words total |
| Conceptual deep-dives (Section 4) | 5 | ~500 words each = 2,500 words total |
| **Total** | **34** | |

**Total new prose: ~3,700 words** — achievable in one focused session.

The CLI extraction can be partially automated by reading each command file and templating the output, which the implementation plan will detail.
