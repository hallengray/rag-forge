# Package Publishing — Design Spec

**Date:** 2026-04-12
**Author:** Femi Adedayo (design), Claude (spec)
**Status:** Approved

## Overview

Make RAG-Forge installable by the public via `npm install -g rag-forge` and `pip install rag-forge-core`. This includes package metadata, a root README, GitHub Actions release automation, and PyPI Trusted Publishers OIDC.

## Packages

### npm (3 packages)

| Package | Type | Install Command |
|---------|------|-----------------|
| `rag-forge` | CLI (global) | `npm install -g rag-forge` |
| `@rag-forge/mcp` | Library | `npm install @rag-forge/mcp` |
| `@rag-forge/shared` | Internal | dependency of CLI and MCP |

### PyPI (3 packages)

| Package | Type | Install Command |
|---------|------|-----------------|
| `rag-forge-core` | Library | `pip install rag-forge-core` |
| `rag-forge-evaluator` | Library | `pip install rag-forge-evaluator` |
| `rag-forge-observability` | Library | `pip install rag-forge-observability` |

## Versioning

All 6 packages share the same version number. Initial release: `0.1.0`. Tag format: `v0.1.0`. All packages bump together on each release.

## Deliverables

### 1. Package Metadata

Add to all npm `package.json` files:
```json
{
  "author": "Femi Adedayo",
  "repository": {
    "type": "git",
    "url": "https://github.com/hallengray/rag-forge.git"
  },
  "homepage": "https://github.com/hallengray/rag-forge",
  "keywords": ["rag", "retrieval-augmented-generation", "evaluation", "llm", "cli"],
  "bugs": {
    "url": "https://github.com/hallengray/rag-forge/issues"
  }
}
```

Add to all Python `pyproject.toml` files:
```toml
[project]
authors = [{ name = "Femi Adedayo" }]
keywords = ["rag", "retrieval-augmented-generation", "evaluation", "llm", "pipeline"]

[project.urls]
Homepage = "https://github.com/hallengray/rag-forge"
Repository = "https://github.com/hallengray/rag-forge"
Issues = "https://github.com/hallengray/rag-forge/issues"
```

### 2. Root README.md

A concise README covering:
- One-line description (from PRD: "Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in")
- Install instructions (npm global + pip for Python packages)
- Quick start: `rag-forge init basic && rag-forge index --source ./docs && rag-forge audit`
- Template list (basic, hybrid, agentic, enterprise, n8n)
- Key commands table (init, index, query, audit, assess, drift, cost, golden, guardrails, serve)
- Link to CONTRIBUTING.md
- License badge

This README is also what npm and PyPI display as the package landing page.

### 3. GitHub Actions Publish Workflow

**File:** `.github/workflows/publish.yml`

**Trigger:** On GitHub Release created with tag matching `v*`

**Jobs:**

**Job 1: verify**
- Checkout, setup Node 20 + pnpm, setup Python 3.11 + uv
- Install all dependencies
- Run full build (`pnpm run build`)
- Run all tests (`pnpm run test`)
- Run lint + typecheck
- If any step fails, the publish jobs don't run

**Job 2: publish-npm** (depends on verify)
- Build all TS packages
- Publish `@rag-forge/shared` first (dependency)
- Publish `@rag-forge/mcp` second
- Publish `rag-forge` last (the CLI)
- Uses `NPM_TOKEN` secret for authentication
- `--access public` for scoped packages

**Job 3: publish-pypi** (depends on verify)
- Build all Python packages with `uv build`
- Publish `rag-forge-core` first
- Publish `rag-forge-evaluator` second
- Publish `rag-forge-observability` third
- Uses PyPI Trusted Publishers (OIDC) — no secrets needed, configured in PyPI account
- Requires `permissions: id-token: write` in the workflow

### 4. Manual Publish Documentation

Add a "Publishing" section to CONTRIBUTING.md with:
- How to do a dry-run: `npm publish --dry-run` and `uv build`
- How to publish manually (emergency fallback)
- How to create a GitHub Release that triggers the automated workflow
- How to set up PyPI Trusted Publishers (one-time setup)
- How to add `NPM_TOKEN` as a GitHub Actions secret (one-time setup)

### 5. Availability Check

Before first publish, verify:
- `npm view rag-forge` returns 404 (name available)
- `pip index versions rag-forge-core` returns nothing (name available)
- `@rag-forge` scope is claimable on npm (or use `npx npm-name-cli @rag-forge/mcp`)

If names are taken, fall back to `@hallengray/rag-forge` scope.

## What Does NOT Change

- Package structure (already correct)
- Build pipeline (Turborepo + tsup + hatchling)
- Entry points (CLI bin field, Python wheel config)
- CI workflow (ci.yml stays as-is for PRs/pushes)

## Pre-Publish Checklist

Before the first release:
1. Verify npm name availability
2. Verify PyPI name availability
3. Set up PyPI Trusted Publisher for the GitHub repo
4. Add `NPM_TOKEN` secret to GitHub repo settings
5. Create GitHub Release with tag `v0.1.0`
