# Package Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make RAG-Forge installable from npm and PyPI via automated GitHub Actions release workflow with PyPI Trusted Publishers OIDC.

**Architecture:** All 6 packages (3 npm + 3 PyPI) get production metadata. A root README.md becomes the npm/PyPI landing page. A `.github/workflows/publish.yml` workflow triggers on GitHub Releases tagged `v*`, runs full quality checks, then publishes to npm (token-based) and PyPI (OIDC). Manual publishing is documented as fallback.

**Tech Stack:** GitHub Actions, npm, PyPI, hatchling, tsup, Turborepo

**Branch:** `feat/package-publishing`

---

### Task 1: npm Package Metadata — CLI

**Files:**
- Modify: `packages/cli/package.json`

- [ ] **Step 1: Add author, repository, homepage, keywords, bugs**

Read the current `packages/cli/package.json`. After the `"description"` field and before `"type"`, add:

```json
  "author": "Femi Adedayo",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/hallengray/rag-forge.git",
    "directory": "packages/cli"
  },
  "homepage": "https://github.com/hallengray/rag-forge#readme",
  "bugs": {
    "url": "https://github.com/hallengray/rag-forge/issues"
  },
  "keywords": [
    "rag",
    "retrieval-augmented-generation",
    "evaluation",
    "llm",
    "cli",
    "rag-pipeline",
    "ragas",
    "deepeval"
  ],
```

- [ ] **Step 2: Verify package.json is valid JSON**

Run: `cd "C:/Users/halle/Downloads/RAGforge" && node -e "JSON.parse(require('fs').readFileSync('packages/cli/package.json', 'utf-8'))"`
Expected: No output (silent success)

- [ ] **Step 3: Commit**

```bash
git add packages/cli/package.json
git commit -m "chore(cli): add publishing metadata to package.json"
```

---

### Task 2: npm Package Metadata — MCP

**Files:**
- Modify: `packages/mcp/package.json`

- [ ] **Step 1: Add metadata**

Same fields as Task 1 but with `"directory": "packages/mcp"`. Keywords for MCP:

```json
  "author": "Femi Adedayo",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/hallengray/rag-forge.git",
    "directory": "packages/mcp"
  },
  "homepage": "https://github.com/hallengray/rag-forge#readme",
  "bugs": {
    "url": "https://github.com/hallengray/rag-forge/issues"
  },
  "keywords": [
    "rag",
    "mcp",
    "model-context-protocol",
    "llm",
    "anthropic",
    "claude"
  ],
```

- [ ] **Step 2: Verify and commit**

```bash
node -e "JSON.parse(require('fs').readFileSync('packages/mcp/package.json', 'utf-8'))"
git add packages/mcp/package.json
git commit -m "chore(mcp): add publishing metadata to package.json"
```

---

### Task 3: npm Package Metadata — Shared

**Files:**
- Modify: `packages/shared/package.json`

- [ ] **Step 1: Add metadata**

Same pattern. Add a `description` field if missing. Keywords:

```json
  "description": "Internal shared utilities for RAG-Forge packages",
  "author": "Femi Adedayo",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/hallengray/rag-forge.git",
    "directory": "packages/shared"
  },
  "homepage": "https://github.com/hallengray/rag-forge#readme",
  "bugs": {
    "url": "https://github.com/hallengray/rag-forge/issues"
  },
  "keywords": ["rag", "rag-forge", "internal"],
```

- [ ] **Step 2: Verify and commit**

```bash
node -e "JSON.parse(require('fs').readFileSync('packages/shared/package.json', 'utf-8'))"
git add packages/shared/package.json
git commit -m "chore(shared): add publishing metadata to package.json"
```

---

### Task 4: PyPI Package Metadata — Core

**Files:**
- Modify: `packages/core/pyproject.toml`

- [ ] **Step 1: Add authors, keywords, project URLs**

Read `packages/core/pyproject.toml`. In the `[project]` section, add:

```toml
authors = [{ name = "Femi Adedayo" }]
keywords = ["rag", "retrieval-augmented-generation", "llm", "pipeline", "chunking", "embedding"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
readme = "README.md"
```

After the `[project]` section (and before `[project.optional-dependencies]` if it exists), add:

```toml
[project.urls]
Homepage = "https://github.com/hallengray/rag-forge"
Repository = "https://github.com/hallengray/rag-forge"
Issues = "https://github.com/hallengray/rag-forge/issues"
Documentation = "https://github.com/hallengray/rag-forge#readme"
```

- [ ] **Step 2: Verify TOML is valid**

Run: `export PATH="$HOME/.local/bin:$PATH" && cd "C:/Users/halle/Downloads/RAGforge" && uv run python -c "import tomllib; tomllib.loads(open('packages/core/pyproject.toml').read())"`
Expected: No output

- [ ] **Step 3: Commit**

```bash
git add packages/core/pyproject.toml
git commit -m "chore(core): add publishing metadata to pyproject.toml"
```

---

### Task 5: PyPI Package Metadata — Evaluator

**Files:**
- Modify: `packages/evaluator/pyproject.toml`

- [ ] **Step 1: Add metadata (same fields as Task 4 with evaluator-specific keywords)**

Add to `[project]`:
```toml
authors = [{ name = "Femi Adedayo" }]
keywords = ["rag", "evaluation", "ragas", "deepeval", "llm-as-judge", "rmm"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
readme = "README.md"
```

Add `[project.urls]`:
```toml
[project.urls]
Homepage = "https://github.com/hallengray/rag-forge"
Repository = "https://github.com/hallengray/rag-forge"
Issues = "https://github.com/hallengray/rag-forge/issues"
Documentation = "https://github.com/hallengray/rag-forge#readme"
```

- [ ] **Step 2: Verify and commit**

```bash
export PATH="$HOME/.local/bin:$PATH"
uv run python -c "import tomllib; tomllib.loads(open('packages/evaluator/pyproject.toml').read())"
git add packages/evaluator/pyproject.toml
git commit -m "chore(evaluator): add publishing metadata to pyproject.toml"
```

---

### Task 6: PyPI Package Metadata — Observability

**Files:**
- Modify: `packages/observability/pyproject.toml`

- [ ] **Step 1: Add metadata**

Add to `[project]`:
```toml
authors = [{ name = "Femi Adedayo" }]
keywords = ["rag", "observability", "opentelemetry", "drift-detection", "tracing"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Monitoring",
]
readme = "README.md"
```

Add `[project.urls]`:
```toml
[project.urls]
Homepage = "https://github.com/hallengray/rag-forge"
Repository = "https://github.com/hallengray/rag-forge"
Issues = "https://github.com/hallengray/rag-forge/issues"
Documentation = "https://github.com/hallengray/rag-forge#readme"
```

- [ ] **Step 2: Verify and commit**

```bash
export PATH="$HOME/.local/bin:$PATH"
uv run python -c "import tomllib; tomllib.loads(open('packages/observability/pyproject.toml').read())"
git add packages/observability/pyproject.toml
git commit -m "chore(observability): add publishing metadata to pyproject.toml"
```

---

### Task 7: Per-Package READMEs for Python Packages

**Files:**
- Create: `packages/core/README.md`
- Create: `packages/evaluator/README.md`
- Create: `packages/observability/README.md`

These README files become the PyPI landing page for each package. They are separate from the root README.

- [ ] **Step 1: Create `packages/core/README.md`**

```markdown
# rag-forge-core

RAG pipeline primitives for the RAG-Forge toolkit: ingestion, chunking, retrieval, context management, and security.

## Installation

```bash
pip install rag-forge-core
```

## Usage

This package provides the building blocks used by the `rag-forge` CLI. For end-user usage, see the [main RAG-Forge documentation](https://github.com/hallengray/rag-forge#readme).

```python
from rag_forge_core.chunking.factory import create_chunker
from rag_forge_core.chunking.config import ChunkConfig

chunker = create_chunker(ChunkConfig(strategy="recursive", chunk_size=512))
chunks = chunker.chunk("Some long document text...", source="doc.md")
```

## Modules

- `rag_forge_core.chunking` — Five chunking strategies (recursive, fixed, semantic, structural, llm-driven)
- `rag_forge_core.retrieval` — Dense, sparse, and hybrid retrieval with reranking
- `rag_forge_core.security` — InputGuard, OutputGuard, PII scanning, prompt injection detection
- `rag_forge_core.context` — Contextual enrichment and semantic caching
- `rag_forge_core.plugins` — Plugin registry for custom extensions

## License

MIT
```

- [ ] **Step 2: Create `packages/evaluator/README.md`**

```markdown
# rag-forge-evaluator

RAG pipeline evaluation engine for the RAG-Forge toolkit: RAGAS, DeepEval, LLM-as-Judge, and the RAG Maturity Model.

## Installation

```bash
pip install rag-forge-evaluator
```

## Usage

```python
from rag_forge_evaluator.assess import RMMAssessor

assessor = RMMAssessor()
result = assessor.assess(config={
    "retrieval_strategy": "hybrid",
    "input_guard_configured": True,
    "output_guard_configured": True,
})
print(result.badge)  # e.g., "RMM-3 Better Trust"
```

## Features

- RMM (RAG Maturity Model) scoring (levels 0-5)
- RAGAS, DeepEval, and LLM-as-Judge evaluators
- Golden set management with traffic sampling
- Cost estimation
- HTML and PDF report generation

## License

MIT
```

- [ ] **Step 3: Create `packages/observability/README.md`**

```markdown
# rag-forge-observability

OpenTelemetry tracing and query drift detection for the RAG-Forge toolkit.

## Installation

```bash
pip install rag-forge-observability
```

## Usage

```python
from rag_forge_observability.drift import DriftDetector, DriftBaseline

baseline = DriftBaseline(embeddings=[[1.0, 0.0, 0.0]])
detector = DriftDetector(threshold=0.15)
report = detector.analyze(current_embeddings=[[0.9, 0.1, 0.0]], baseline=baseline)
print(f"Drift detected: {report.is_drifting}")
```

## Features

- OpenTelemetry tracing for all RAG pipeline stages
- Query drift detection with baseline comparison
- Centroid-based cosine distance analysis

## License

MIT
```

- [ ] **Step 4: Commit**

```bash
git add packages/core/README.md packages/evaluator/README.md packages/observability/README.md
git commit -m "docs: add per-package READMEs for PyPI landing pages"
```

---

### Task 8: Root README.md

**Files:**
- Create: `README.md` (or modify if exists)

- [ ] **Step 1: Check if README.md exists**

Run: `ls README.md 2>&1 || echo "missing"`

- [ ] **Step 2: Create the root README**

```markdown
# RAG-Forge

> Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in — not bolted on after deployment.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

RAG-Forge bridges the gap between **building** RAG pipelines and **knowing whether they work**. It scaffolds production-ready pipelines, runs continuous evaluation as a CI/CD gate, and assesses any existing RAG system against the **RAG Maturity Model (RMM-0 through RMM-5)**.

## Installation

**CLI (Node.js 20+):**

```bash
npm install -g rag-forge
```

**Python packages (Python 3.11+):**

```bash
pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

## Quick Start

```bash
# Scaffold a new RAG project
rag-forge init basic

cd my-rag-project

# Index your documents
rag-forge index --source ./docs

# Run evaluation
rag-forge audit --golden-set eval/golden_set.json

# Score against RAG Maturity Model
rag-forge assess --audit-report reports/audit-report.json
```

## Templates

| Template | Use Case |
|----------|----------|
| `basic` | First RAG project, simple Q&A |
| `hybrid` | Production-ready document Q&A with reranking |
| `agentic` | Multi-hop reasoning with query decomposition |
| `enterprise` | Regulated industries with full security suite |
| `n8n` | AI automation agency deployments |

## Commands

| Category | Commands |
|----------|----------|
| **Scaffolding** | `init`, `add` |
| **Ingestion** | `parse`, `chunk`, `index` |
| **Query** | `query`, `inspect` |
| **Evaluation** | `audit`, `assess`, `golden add`, `golden validate` |
| **Operations** | `report`, `cache stats`, `drift report`, `cost` |
| **Security** | `guardrails test`, `guardrails scan-pii` |
| **Integration** | `serve --mcp`, `n8n export` |

Run `rag-forge --help` for the full command reference.

## RAG Maturity Model

| Level | Name | Exit Criteria |
|-------|------|---------------|
| RMM-0 | Naive | Basic vector search works |
| RMM-1 | Better Recall | Hybrid search, Recall@5 > 70% |
| RMM-2 | Better Precision | Reranker active, nDCG@10 +10% |
| RMM-3 | Better Trust | Guardrails, faithfulness > 85% |
| RMM-4 | Better Workflow | Caching, P95 < 4s, cost tracking |
| RMM-5 | Enterprise | Drift detection, CI/CD gates, adversarial tests |

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and contribution guidelines.

## License

MIT — see [LICENSE](./LICENSE)
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add root README.md as npm/PyPI landing page"
```

---

### Task 9: GitHub Actions Publish Workflow

**Files:**
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Create the publish workflow**

```yaml
name: Publish

on:
  release:
    types: [published]

permissions:
  contents: read
  id-token: write  # Required for PyPI Trusted Publishers OIDC

jobs:
  verify:
    name: Verify Build & Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          registry-url: https://registry.npmjs.org

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Setup uv
        uses: astral-sh/setup-uv@v3

      - name: Install Node dependencies
        run: pnpm install --frozen-lockfile

      - name: Install Python dependencies
        run: uv sync --all-packages

      - name: Build TypeScript packages
        run: pnpm run build

      - name: Lint
        run: pnpm run lint

      - name: Type check
        run: pnpm run typecheck

      - name: Run tests
        run: pnpm run test

  publish-npm:
    name: Publish to npm
    needs: verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          registry-url: https://registry.npmjs.org

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build all packages
        run: pnpm run build

      - name: Publish @rag-forge/shared
        working-directory: packages/shared
        run: npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      - name: Publish @rag-forge/mcp
        working-directory: packages/mcp
        run: npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      - name: Publish rag-forge (CLI)
        working-directory: packages/cli
        run: npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  publish-pypi:
    name: Publish to PyPI
    needs: verify
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC trusted publishing
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Setup uv
        uses: astral-sh/setup-uv@v3

      - name: Build rag-forge-core
        working-directory: packages/core
        run: uv build

      - name: Publish rag-forge-core to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/core/dist/

      - name: Build rag-forge-evaluator
        working-directory: packages/evaluator
        run: uv build

      - name: Publish rag-forge-evaluator to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/evaluator/dist/

      - name: Build rag-forge-observability
        working-directory: packages/observability
        run: uv build

      - name: Publish rag-forge-observability to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/observability/dist/
```

- [ ] **Step 2: Verify YAML is valid**

Run: `cd "C:/Users/halle/Downloads/RAGforge" && python -c "import yaml; yaml.safe_load(open('.github/workflows/publish.yml'))"`
Expected: No output

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add publish workflow for npm + PyPI on GitHub Releases"
```

---

### Task 10: Manual Publishing Documentation

**Files:**
- Modify: `CONTRIBUTING.md` (append a Publishing section)

- [ ] **Step 1: Append the Publishing section**

Add this section at the end of `CONTRIBUTING.md`:

```markdown

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
   - Publish 3 npm packages (shared → mcp → cli order)
   - Publish 3 PyPI packages (core → evaluator → observability)

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
3. Add as GitHub Actions secret: `Settings → Secrets and variables → Actions → New repository secret`
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
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add publishing workflow to contributor guide"
```

---

### Task 11: Availability Check Script

**Files:**
- Create: `scripts/check-publish-names.sh`

- [ ] **Step 1: Create the check script**

```bash
#!/usr/bin/env bash
# Check whether RAG-Forge package names are available on npm and PyPI.
# Run before the first publish.

set -e

echo "Checking npm name availability..."
echo ""

check_npm() {
    local name="$1"
    if npm view "$name" version &>/dev/null; then
        echo "  TAKEN: $name"
        return 1
    else
        echo "  AVAILABLE: $name"
        return 0
    fi
}

check_pypi() {
    local name="$1"
    if curl -sf "https://pypi.org/pypi/$name/json" &>/dev/null; then
        echo "  TAKEN: $name"
        return 1
    else
        echo "  AVAILABLE: $name"
        return 0
    fi
}

echo "npm packages:"
check_npm "rag-forge" || true
check_npm "@rag-forge/mcp" || true
check_npm "@rag-forge/shared" || true

echo ""
echo "PyPI packages:"
check_pypi "rag-forge-core" || true
check_pypi "rag-forge-evaluator" || true
check_pypi "rag-forge-observability" || true

echo ""
echo "Done. If any names are TAKEN, you need to either:"
echo "  1. Use a different scope (e.g., @hallengray/rag-forge)"
echo "  2. Use a different name suffix"
echo "  3. Contact npm/PyPI support if you believe they should be available"
```

- [ ] **Step 2: Make executable and verify**

```bash
chmod +x scripts/check-publish-names.sh
ls -l scripts/check-publish-names.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/check-publish-names.sh
git commit -m "chore: add script to check npm and PyPI name availability"
```

---

### Task 12: Final Build Quality Check + PR

- [ ] **Step 1: Run full build quality check**

```bash
export PATH="$HOME/.local/bin:$PATH"
cd "C:/Users/halle/Downloads/RAGforge"
pnpm run build
pnpm run lint
pnpm run typecheck
pnpm run test
```

Expected: All pass with zero errors.

- [ ] **Step 2: Verify all 6 package files have metadata**

```bash
node -e "const p = JSON.parse(require('fs').readFileSync('packages/cli/package.json', 'utf-8')); console.log(p.author, p.repository?.url, p.keywords?.length);"
node -e "const p = JSON.parse(require('fs').readFileSync('packages/mcp/package.json', 'utf-8')); console.log(p.author, p.repository?.url, p.keywords?.length);"
node -e "const p = JSON.parse(require('fs').readFileSync('packages/shared/package.json', 'utf-8')); console.log(p.author, p.repository?.url, p.keywords?.length);"
uv run python -c "import tomllib; print(tomllib.loads(open('packages/core/pyproject.toml').read())['project'].get('authors'))"
uv run python -c "import tomllib; print(tomllib.loads(open('packages/evaluator/pyproject.toml').read())['project'].get('authors'))"
uv run python -c "import tomllib; print(tomllib.loads(open('packages/observability/pyproject.toml').read())['project'].get('authors'))"
```

Each should print non-empty values (the author name and counts).

- [ ] **Step 3: Push and create PR**

```bash
git push -u origin feat/package-publishing
gh pr create --title "feat: package publishing infrastructure for npm + PyPI" --body "$(cat <<'EOF'
## Summary
- Adds publishing metadata (author, repository, keywords, classifiers) to all 6 packages
- Creates root README.md as the npm/PyPI landing page
- Creates per-package READMEs for the 3 Python packages (PyPI requires per-package READMEs)
- Adds GitHub Actions publish workflow triggered by GitHub Releases
- Publishes 3 npm packages (token-based) and 3 PyPI packages (Trusted Publishers OIDC)
- Documents manual publishing as emergency fallback in CONTRIBUTING.md
- Adds availability check script for first-time publish

## What's Required Before First Release
1. Run `bash scripts/check-publish-names.sh` to verify name availability
2. Add `NPM_TOKEN` secret to GitHub repo settings
3. Configure PyPI Trusted Publishers for `rag-forge-core`, `rag-forge-evaluator`, `rag-forge-observability`

## Test plan
- [x] All 6 package files have valid metadata
- [x] YAML workflow file is valid
- [x] `pnpm run build && pnpm run lint && pnpm run typecheck && pnpm run test` pass
EOF
)"
```
