# RAG-Forge

Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in.

## Architecture

Polyglot monorepo: TypeScript (CLI + MCP server) and Python (core pipeline + evaluator + observability).

```
rag-forge/
├── packages/cli/          # TypeScript — Commander.js CLI (the `rag-forge` command)
├── packages/mcp/          # TypeScript — MCP server (@modelcontextprotocol/sdk)
├── packages/core/         # Python 3.11+ — RAG pipeline primitives
├── packages/evaluator/    # Python — RAGAS + DeepEval + LLM-as-Judge
├── packages/observability/ # Python — OpenTelemetry + Langfuse
├── templates/             # Project templates (basic, hybrid, agentic, enterprise, n8n)
├── tests/                 # Cross-package integration tests
└── docs/                  # Documentation
```

**Language boundaries:** CLI and MCP server are TypeScript (Node 20+). All RAG logic (chunking, retrieval, evaluation, tracing) is Python. The CLI delegates to Python via subprocess bridge (`uv run python -m <module>`).

**Dependency flow:** CLI → Core, CLI → Evaluator (via subprocess). MCP → Core, MCP → Evaluator (via subprocess). Evaluator → Core. Observability is standalone, imported by Core.

## Build & Test Commands

```bash
# Full monorepo
pnpm run build          # Build all TS packages via Turborepo
pnpm run test           # Run all tests (Vitest + pytest)
pnpm run lint           # Lint all (ESLint + Ruff)
pnpm run typecheck      # Type-check all (tsc + mypy)

# TypeScript only
pnpm run test:ts        # Vitest only
turbo run build --filter=rag-forge  # Build CLI only

# Python only
pnpm run test:py        # pytest only
uv run ruff check .     # Ruff lint
uv run mypy packages/core/src packages/evaluator/src packages/observability/src

# Single package
cd packages/cli && pnpm run build
cd packages/core && uv run pytest
```

## Code Standards

### TypeScript
- Strict mode, no `any`, no `@ts-ignore`
- ESM modules, Node 20+ target
- ESLint 9 flat config with typescript-eslint strict + stylistic
- Consistent type imports (`import type { X } from ...`)
- Bundled with tsup

### Python
- Type hints on all functions and methods
- Pydantic models for all configuration (not raw dicts)
- Ruff for linting and formatting (line-length 100)
- mypy for type checking
- pytest for testing

## Key Conventions

- **Chunk configs validated at init time** (fail-fast pattern via Pydantic)
- **Every pipeline stage emits an OTEL span** with standardized attributes
- **Golden sets live in** `tests/fixtures/*.json` or template `eval/` dirs
- **Never hardcode embedding model names** — always use config
- **CLI delegates to Python via subprocess bridge** — see `packages/cli/src/lib/python-bridge.ts`
- **Templates generate editable source code** (shadcn/ui model, not framework dependencies)
- **Evaluation thresholds** are defined in `rag-forge.config.ts` at project root
- **RMM levels (0-5)** are the scoring framework — see `packages/evaluator/src/rag_forge_evaluator/maturity.py`

## Monorepo Tooling

- **Turborepo** orchestrates TypeScript package tasks (build, test, lint, typecheck)
- **pnpm workspaces** manage TypeScript packages (packages/cli, packages/mcp)
- **uv workspaces** manage Python packages (packages/core, packages/evaluator, packages/observability)
- Root `package.json` scripts coordinate both ecosystems
