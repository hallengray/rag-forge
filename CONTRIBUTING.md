# Contributing to RAG-Forge

Thank you for your interest in contributing to RAG-Forge! This guide covers everything you need to get started.

## Development Setup

### Prerequisites

- **Node.js 20+** and **pnpm** (TypeScript packages)
- **Python 3.11+** and **uv** (Python packages)
- **Git**

### Clone and Install

```bash
git clone https://github.com/hallengray/RAGforge.git
cd RAGforge

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

```
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
