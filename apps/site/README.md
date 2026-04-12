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
