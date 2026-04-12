# Contributing to RAG-Forge

Thank you for your interest in contributing to RAG-Forge! This guide covers everything you need to get started.

## Development Setup

### Prerequisites

- **Node.js 20+** and **pnpm** (TypeScript packages)
- **Python 3.11+** and **uv** (Python packages)
- **Git**

### Clone and Install

```bash
git clone https://github.com/hallengray/rag-forge.git
cd rag-forge

# Install TypeScript dependencies
pnpm install

# Install Python dependencies
uv sync --all-packages
```

### Verify Setup

```bash
pnpm run build        # Build all TypeScript packages
pnpm run test         # Run all tests (Vitest + pytest)
pnpm run lint         # Lint all (ESLint + Ruff)
pnpm run typecheck    # Type-check all (tsc + mypy)
```

All four commands must pass with zero errors before submitting a PR.

## Project Structure

```text
packages/cli/          # TypeScript — CLI interface (Commander.js)
packages/mcp/          # TypeScript — MCP server
packages/core/         # Python — RAG pipeline primitives
packages/evaluator/    # Python — Evaluation engine
packages/observability/ # Python — OpenTelemetry + drift detection
templates/             # Project templates
```

**Language boundaries:** CLI and MCP are TypeScript. All RAG logic is Python. The CLI calls Python via `uv run python -m <module>`.

## Writing a Custom Plugin

RAG-Forge supports custom plugins for chunking strategies, retrieval strategies, and evaluation metrics.

### Custom Chunking Strategy

1. Create a Python package with your strategy:

```python
# my_chunker/strategy.py
from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig


class MyCustomChunker(ChunkStrategy):
    def chunk(self, text: str, source: str) -> list[Chunk]:
        # Your chunking logic here
        ...

    def preview(self, text: str, source: str) -> list[Chunk]:
        return self.chunk(text, source)

    def stats(self, chunks: list[Chunk]) -> ChunkStats:
        # Compute statistics
        ...
```

2. Register via entry points in your `pyproject.toml`:

```toml
[project.entry-points."rag_forge.chunkers"]
my-strategy = "my_chunker.strategy:MyCustomChunker"
```

3. Install your package and RAG-Forge will discover it automatically:

```bash
pip install my-chunker-package
rag-forge index --source ./docs --strategy my-strategy
```

### Custom Evaluation Metric

Register under `rag_forge.metrics`:

```toml
[project.entry-points."rag_forge.metrics"]
my-metric = "my_metrics:MyMetricEvaluator"
```

## Code Standards

### TypeScript
- Strict mode, no `any`, no `@ts-ignore`
- ESM modules, Node 20+ target
- ESLint 9 flat config

### Python
- Type hints on all functions
- Pydantic models for configuration
- Ruff for linting (line-length 100)
- mypy for type checking

## Testing

- **Python:** `pytest` with tests alongside packages (`packages/core/tests/`)
- **TypeScript:** Vitest (`packages/cli/__tests__/`)
- Write tests before implementation (TDD)
- Every PR must include tests for new functionality

## PR Workflow

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes with tests
3. Run the full quality check: `pnpm run build && pnpm run lint && pnpm run typecheck && pnpm run test`
4. Push and create a PR against `main`
5. CodeRabbit will automatically review your PR
6. Address review feedback
7. Merge after approval

### Commit Messages

Use conventional commit format:

```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore
```

## Questions?

Open an issue on GitHub for questions about contributing.

## Publishing

RAG-Forge publishes 6 packages: 3 to npm and 3 to PyPI. All releases are automated via GitHub Actions.

### Automated Release (Standard Workflow)

1. Bump the version in all 6 package files (must match):
   - `packages/cli/package.json`
   - `packages/mcp/package.json`
   - `packages/shared/package.json`
   - `packages/core/pyproject.toml`
   - `packages/evaluator/pyproject.toml`
   - `packages/observability/pyproject.toml`

2. Commit the version bump and push to main.

3. Create a GitHub Release:
   - Tag: `v0.1.0` (matching the version)
   - Title: `v0.1.0`
   - Description: changelog notes
   - Publish

4. The `publish.yml` workflow will:
   - Run full quality checks (build, lint, typecheck, test)
   - Publish 3 npm packages (shared -> mcp -> cli order)
   - Publish 3 PyPI packages (core -> evaluator -> observability)

### Manual Publishing (Emergency Fallback)

**Dry-run npm:**
```bash
cd packages/cli
npm publish --dry-run
```

**Dry-run PyPI:**
```bash
cd packages/core
uv build
ls dist/  # Verify wheel and sdist exist
```

**Actual manual publish (npm):**
```bash
# You need NPM_TOKEN env var set
cd packages/shared && npm publish --access public
cd ../mcp && npm publish --access public
cd ../cli && npm publish --access public
```

**Actual manual publish (PyPI):**
```bash
# You need a PyPI API token
cd packages/core && uv build && uv publish
cd ../evaluator && uv build && uv publish
cd ../observability && uv build && uv publish
```

### One-Time Setup (Repo Maintainer Only)

**npm:**
1. Generate an npm access token at https://www.npmjs.com/settings/YOUR_USERNAME/tokens
2. Token type: "Automation" (or "Granular Access" with publish scope)
3. Add as GitHub Actions secret: `Settings -> Secrets and variables -> Actions -> New repository secret`
4. Name: `NPM_TOKEN`
5. Value: the token string

**PyPI Trusted Publishers:**
1. Go to https://pypi.org/manage/account/publishing/
2. Add a new pending publisher:
   - PyPI Project Name: `rag-forge-core` (repeat for each package)
   - Owner: `hallengray`
   - Repository name: `rag-forge`
   - Workflow name: `publish.yml`
   - Environment name: (leave blank)
3. Repeat for `rag-forge-evaluator` and `rag-forge-observability`
4. After the first successful publish, the publisher becomes "trusted"
