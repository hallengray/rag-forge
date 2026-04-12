# Phase 2D: MCP Server + Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the Python bridge into a shared package, wire the MCP server tools to real Python pipelines, add `serve --mcp` command, and build `hybrid` and `enterprise` project templates.

**Architecture:** A new `@rag-forge/shared` package holds the Python bridge. Both CLI and MCP import from it. MCP tool handlers call Python modules via the bridge and return JSON results. Templates follow the basic template's file structure with different config values.

**Tech Stack:** TypeScript (tsup, @modelcontextprotocol/sdk, execa, Commander.js), Python 3.11+.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/shared/package.json` | Shared package metadata |
| `packages/shared/tsconfig.json` | TypeScript config |
| `packages/shared/tsup.config.ts` | Build config |
| `packages/shared/src/python-bridge.ts` | `runPythonModule`, `checkPythonAvailable` |
| `packages/mcp/src/server.ts` | `startServer()` with stdio transport |
| `packages/mcp/src/main.ts` | CLI entry point for MCP server |
| `packages/cli/src/commands/serve.ts` | `rag-forge serve --mcp` command |
| `templates/hybrid/project/pyproject.toml` | Hybrid template package config |
| `templates/hybrid/project/README.md` | Hybrid template docs |
| `templates/hybrid/project/src/config.py` | Hybrid pipeline config |
| `templates/hybrid/project/src/pipeline.py` | Hybrid pipeline example |
| `templates/hybrid/project/eval/config.yaml` | Hybrid eval config |
| `templates/hybrid/project/eval/golden_set.json` | Hybrid golden set |
| `templates/enterprise/project/pyproject.toml` | Enterprise template package config |
| `templates/enterprise/project/README.md` | Enterprise template docs |
| `templates/enterprise/project/src/config.py` | Enterprise pipeline config |
| `templates/enterprise/project/src/pipeline.py` | Enterprise pipeline example |
| `templates/enterprise/project/eval/config.yaml` | Enterprise eval config |
| `templates/enterprise/project/eval/golden_set.json` | Enterprise golden set |
| `templates/enterprise/project/.github/workflows/rag-audit.yml` | CI gate workflow |

### Modified Files

| File | Change |
|------|--------|
| `pnpm-workspace.yaml` | Add `packages/shared` |
| `packages/cli/package.json` | Add `@rag-forge/shared` dep, remove `execa` |
| `packages/cli/src/lib/python-bridge.ts` | Re-export from `@rag-forge/shared` |
| `packages/cli/src/index.ts` | Register serve command |
| `packages/mcp/package.json` | Add `@rag-forge/shared` dep |
| `packages/mcp/src/tools/rag-query.ts` | Replace stub with real bridge call |
| `packages/mcp/src/tools/rag-audit.ts` | Replace stub with real bridge call |
| `packages/mcp/src/tools/rag-status.ts` | Replace stub with real bridge call |
| `packages/mcp/src/index.ts` | Update imports |
| `packages/mcp/tsup.config.ts` | Add `main.ts` entry point |
| `packages/core/src/rag_forge_core/cli.py` | Add `status` subcommand |
| `templates/hybrid/README.md` | Replace stub |
| `templates/enterprise/README.md` | Replace stub |

---

## Task 1: Create Shared Bridge Package

**Files:**
- Create: `packages/shared/package.json`
- Create: `packages/shared/tsconfig.json`
- Create: `packages/shared/tsup.config.ts`
- Create: `packages/shared/src/python-bridge.ts`
- Modify: `pnpm-workspace.yaml`

- [ ] **Step 1: Create package.json**

Create `packages/shared/package.json`:

```json
{
  "name": "@rag-forge/shared",
  "version": "0.1.0",
  "description": "Shared utilities for RAG-Forge packages",
  "type": "module",
  "exports": {
    ".": {
      "import": "./dist/python-bridge.js",
      "types": "./dist/python-bridge.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build": "tsup",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "execa": "^9.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "tsup": "^8.0.0",
    "typescript": "^5.5.0"
  },
  "engines": {
    "node": ">=20.0.0"
  },
  "license": "MIT"
}
```

- [ ] **Step 2: Create tsconfig.json**

Create `packages/shared/tsconfig.json`:

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"],
  "exclude": ["dist", "node_modules"]
}
```

- [ ] **Step 3: Create tsup.config.ts**

Create `packages/shared/tsup.config.ts`:

```typescript
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/python-bridge.ts"],
  format: ["esm"],
  target: "node20",
  dts: true,
  clean: true,
  sourcemap: true,
});
```

- [ ] **Step 4: Create python-bridge.ts**

Create `packages/shared/src/python-bridge.ts`:

```typescript
import { execa } from "execa";

export interface PythonBridgeOptions {
  module: string;
  args?: string[];
  cwd?: string;
}

export interface PythonBridgeResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export async function runPythonModule(options: PythonBridgeOptions): Promise<PythonBridgeResult> {
  const { module, args = [], cwd } = options;

  try {
    const result = await execa("uv", ["run", "python", "-m", module, ...args], {
      cwd,
      reject: false,
    });

    return {
      stdout: result.stdout,
      stderr: result.stderr,
      exitCode: result.exitCode ?? 0,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return {
      stdout: "",
      stderr: message,
      exitCode: 1,
    };
  }
}

export async function checkPythonAvailable(): Promise<boolean> {
  try {
    const result = await execa("uv", ["run", "python", "--version"], { reject: false });
    return result.exitCode === 0;
  } catch {
    return false;
  }
}
```

Note: the shared bridge does NOT use the CLI's `logger` — it's a pure utility. Error logging is done by the caller (CLI or MCP).

- [ ] **Step 5: Update pnpm-workspace.yaml**

Replace the full contents of `pnpm-workspace.yaml`:

```yaml
packages:
  - packages/shared
  - packages/cli
  - packages/mcp

autoApproveBuilds: true
```

- [ ] **Step 6: Install dependencies**

Run: `pnpm install`
Expected: Install succeeds, `@rag-forge/shared` is linked.

- [ ] **Step 7: Build the shared package**

Run: `cd packages/shared && pnpm run build`
Expected: Build succeeds, `dist/python-bridge.js` and `dist/python-bridge.d.ts` produced.

- [ ] **Step 8: Commit**

```bash
git add packages/shared/ pnpm-workspace.yaml
git commit -m "feat(shared): create @rag-forge/shared package with Python bridge"
```

---

## Task 2: Update CLI to Use Shared Bridge

**Files:**
- Modify: `packages/cli/package.json`
- Modify: `packages/cli/src/lib/python-bridge.ts`

- [ ] **Step 1: Update CLI package.json**

In `packages/cli/package.json`, add `@rag-forge/shared` to dependencies and remove `execa`:

Change the `"dependencies"` section from:
```json
  "dependencies": {
    "chalk": "^5.3.0",
    "commander": "^12.0.0",
    "cosmiconfig": "^9.0.0",
    "execa": "^9.0.0",
    "ora": "^8.0.0",
    "zod": "^3.23.0"
  },
```

To:
```json
  "dependencies": {
    "@rag-forge/shared": "workspace:*",
    "chalk": "^5.3.0",
    "commander": "^12.0.0",
    "cosmiconfig": "^9.0.0",
    "ora": "^8.0.0",
    "zod": "^3.23.0"
  },
```

- [ ] **Step 2: Replace python-bridge.ts with re-export**

Replace the full contents of `packages/cli/src/lib/python-bridge.ts`:

```typescript
export {
  runPythonModule,
  checkPythonAvailable,
} from "@rag-forge/shared";
export type {
  PythonBridgeOptions,
  PythonBridgeResult,
} from "@rag-forge/shared";
```

- [ ] **Step 3: Install and build**

Run: `pnpm install && pnpm run build`
Expected: Install succeeds (execa removed from CLI, shared linked). Build succeeds for all packages.

- [ ] **Step 4: Run CLI tests to verify nothing broke**

Run: `cd packages/cli && pnpm run typecheck`
Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add packages/cli/package.json packages/cli/src/lib/python-bridge.ts pnpm-lock.yaml
git commit -m "refactor(cli): use @rag-forge/shared for Python bridge"
```

---

## Task 3: Wire MCP Tools to Real Bridge

**Files:**
- Modify: `packages/mcp/package.json`
- Modify: `packages/mcp/src/tools/rag-query.ts`
- Modify: `packages/mcp/src/tools/rag-audit.ts`
- Modify: `packages/mcp/src/tools/rag-status.ts`

- [ ] **Step 1: Add shared dependency to MCP package.json**

In `packages/mcp/package.json`, add `@rag-forge/shared` to dependencies:

```json
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "@rag-forge/shared": "workspace:*",
    "zod": "^3.23.0"
  },
```

- [ ] **Step 2: Replace rag-query.ts stub**

Replace the full contents of `packages/mcp/src/tools/rag-query.ts`:

```typescript
import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragQuerySchema = z.object({
  query: z.string().describe("The question to ask the RAG pipeline"),
  top_k: z.number().int().min(1).max(100).default(5).describe("Number of chunks to retrieve"),
  agent_mode: z
    .boolean()
    .default(false)
    .describe("Enable multi-agent query decomposition for complex queries"),
});

export type RagQueryInput = z.infer<typeof ragQuerySchema>;

export async function handleRagQuery(input: RagQueryInput): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: [
      "query",
      "--question", input.query,
      "--top-k", String(input.top_k),
      "--embedding", "mock",
      "--generator", "mock",
      "--strategy", "dense",
    ],
  });

  if (result.exitCode !== 0) {
    return JSON.stringify({
      status: "error",
      message: result.stderr || "Query failed",
    });
  }

  return result.stdout;
}
```

- [ ] **Step 3: Replace rag-audit.ts stub**

Replace the full contents of `packages/mcp/src/tools/rag-audit.ts`:

```typescript
import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragAuditSchema = z.object({
  golden_set_path: z.string().optional().describe("Path to golden set JSON file"),
  metrics: z
    .array(z.string())
    .optional()
    .describe("Specific metrics to evaluate (default: all)"),
});

export type RagAuditInput = z.infer<typeof ragAuditSchema>;

export async function handleRagAudit(input: RagAuditInput): Promise<string> {
  const args = ["audit", "--judge", "mock"];

  if (input.golden_set_path) {
    args.push("--golden-set", input.golden_set_path);
  }

  const result = await runPythonModule({
    module: "rag_forge_evaluator.cli",
    args,
  });

  if (result.exitCode !== 0) {
    return JSON.stringify({
      status: "error",
      message: result.stderr || "Audit failed",
    });
  }

  return result.stdout;
}
```

- [ ] **Step 4: Replace rag-status.ts stub**

Replace the full contents of `packages/mcp/src/tools/rag-status.ts`:

```typescript
import { runPythonModule } from "@rag-forge/shared";

export async function handleRagStatus(): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: ["status"],
  });

  if (result.exitCode !== 0) {
    return JSON.stringify({
      status: "error",
      message: result.stderr || "Failed to get pipeline status",
    });
  }

  return result.stdout;
}
```

- [ ] **Step 5: Install, build, and typecheck**

Run: `pnpm install && cd packages/mcp && pnpm run build && pnpm run typecheck`
Expected: All succeed.

- [ ] **Step 6: Commit**

```bash
git add packages/mcp/package.json packages/mcp/src/tools/ pnpm-lock.yaml
git commit -m "feat(mcp): wire MCP tools to real Python bridge"
```

---

## Task 4: Python Status Subcommand

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`

- [ ] **Step 1: Add status subcommand**

Read the current `packages/core/src/rag_forge_core/cli.py`. Add the following:

1. Add a new function after `cmd_query`:

```python
def cmd_status(args: argparse.Namespace) -> None:
    """Check pipeline status."""
    collection = args.collection or "rag-forge"
    store = QdrantStore()
    try:
        count = store.count(collection)
        indexed = count > 0
    except (ValueError, KeyError):
        count = 0
        indexed = False

    output = {
        "indexed": indexed,
        "collection": collection,
        "chunk_count": count,
    }
    json.dump(output, sys.stdout)
```

2. In `main()`, add a new subparser after the query parser:

```python
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("--collection", help="Collection name", default="rag-forge")
```

3. Add the dispatch in `main()`:

```python
    elif args.command == "status":
        cmd_status(args)
```

- [ ] **Step 2: Verify the subcommand works**

Run: `cd packages/core && uv run python -m rag_forge_core.cli status --help`
Expected: Shows `--collection` option.

Run: `cd packages/core && uv run python -m rag_forge_core.cli status`
Expected: JSON output like `{"indexed": false, "collection": "rag-forge", "chunk_count": 0}`

- [ ] **Step 3: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(core): add status subcommand to Python CLI"
```

---

## Task 5: MCP Server Entry Point

**Files:**
- Create: `packages/mcp/src/server.ts`
- Create: `packages/mcp/src/main.ts`
- Modify: `packages/mcp/tsup.config.ts` (or create if missing)

- [ ] **Step 1: Create server.ts**

Create `packages/mcp/src/server.ts`:

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./index.js";

export async function startServer(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
```

- [ ] **Step 2: Create main.ts**

Create `packages/mcp/src/main.ts`:

```typescript
import { startServer } from "./server.js";

startServer().catch((error) => {
  console.error("MCP server failed to start:", error);
  process.exit(1);
});
```

- [ ] **Step 3: Update tsup.config.ts**

Check if `packages/mcp/tsup.config.ts` exists. If it does, update it. If not, create it:

```typescript
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/main.ts"],
  format: ["esm"],
  target: "node20",
  dts: true,
  clean: true,
  sourcemap: true,
});
```

The key change: `entry` now includes both `src/index.ts` (library) and `src/main.ts` (CLI entry point).

- [ ] **Step 4: Build and verify**

Run: `cd packages/mcp && pnpm run build`
Expected: Build produces `dist/index.js`, `dist/main.js`, `dist/server.js`.

- [ ] **Step 5: Commit**

```bash
git add packages/mcp/src/server.ts packages/mcp/src/main.ts packages/mcp/tsup.config.ts
git commit -m "feat(mcp): add MCP server entry point with stdio transport"
```

---

## Task 6: CLI `serve --mcp` Command

**Files:**
- Create: `packages/cli/src/commands/serve.ts`
- Modify: `packages/cli/src/index.ts`

- [ ] **Step 1: Create serve.ts**

Create `packages/cli/src/commands/serve.ts`:

```typescript
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";

function getMcpMainPath(): string {
  // Resolve the MCP server's main.js entry point
  // In the monorepo, this is at packages/mcp/dist/main.js
  const currentDir = fileURLToPath(new URL(".", import.meta.url));
  return resolve(currentDir, "..", "..", "..", "mcp", "dist", "main.js");
}

export function registerServeCommand(program: Command): void {
  program
    .command("serve")
    .option("--mcp", "Launch MCP server on stdio")
    .option("-p, --port <number>", "Port for HTTP transport (not yet supported)")
    .description("Start the RAG-Forge server")
    .action(async (options: { mcp?: boolean; port?: string }) => {
      if (!options.mcp) {
        logger.error("Please specify a server mode. Currently supported: --mcp");
        process.exit(1);
      }

      const mcpMain = getMcpMainPath();

      logger.info("Starting MCP server on stdio...");
      logger.debug(`MCP entry point: ${mcpMain}`);

      try {
        const { execa } = await import("execa");
        await execa("node", [mcpMain], {
          stdio: "inherit",
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        logger.error(`MCP server failed: ${message}`);
        process.exit(1);
      }
    });
}
```

- [ ] **Step 2: Register serve command in index.ts**

Replace the full contents of `packages/cli/src/index.ts`:

```typescript
import { Command } from "commander";
import { registerInitCommand } from "./commands/init.js";
import { registerIndexCommand } from "./commands/index.js";
import { registerAuditCommand } from "./commands/audit.js";
import { registerQueryCommand } from "./commands/query.js";
import { registerServeCommand } from "./commands/serve.js";

const program = new Command();

program
  .name("rag-forge")
  .description(
    "Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in",
  )
  .version("0.1.0");

registerInitCommand(program);
registerIndexCommand(program);
registerAuditCommand(program);
registerQueryCommand(program);
registerServeCommand(program);

program.parse();
```

- [ ] **Step 3: Build and verify**

Run: `cd packages/cli && pnpm run build && pnpm run typecheck`
Expected: Build and typecheck succeed.

- [ ] **Step 4: Commit**

```bash
git add packages/cli/src/commands/serve.ts packages/cli/src/index.ts
git commit -m "feat(cli): add serve --mcp command to launch MCP server"
```

---

## Task 7: Hybrid Template

**Files:**
- Create: `templates/hybrid/project/pyproject.toml`
- Create: `templates/hybrid/project/README.md`
- Create: `templates/hybrid/project/src/config.py`
- Create: `templates/hybrid/project/src/pipeline.py`
- Create: `templates/hybrid/project/eval/config.yaml`
- Create: `templates/hybrid/project/eval/golden_set.json`
- Modify: `templates/hybrid/README.md`

- [ ] **Step 1: Create pyproject.toml**

Create `templates/hybrid/project/pyproject.toml`:

```toml
[project]
name = "my-rag-pipeline"
version = "0.1.0"
description = "A hybrid RAG pipeline with BM25 + vector search, reranking, and contextual enrichment"
requires-python = ">=3.11"
dependencies = [
    "rag-forge-core[cohere]",
    "rag-forge-evaluator",
    "qdrant-client>=1.9",
    "sentence-transformers>=3.0",
]

[tool.rag-forge]
template = "hybrid"
chunk_strategy = "recursive"
chunk_size = 512
overlap_ratio = 0.1
vector_db = "qdrant"
embedding_model = "BAAI/bge-m3"
retrieval_strategy = "hybrid"
retrieval_alpha = 0.6
reranker = "cohere"
enrich = true
```

- [ ] **Step 2: Create README.md**

Create `templates/hybrid/project/README.md`:

```markdown
# Hybrid RAG Pipeline

A production-ready RAG pipeline with hybrid retrieval (BM25 + vector), Cohere reranking, and contextual enrichment. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Hybrid search**: BM25 sparse + dense vector retrieval with Reciprocal Rank Fusion
- **Reranking**: Cohere Rerank API for improved precision
- **Contextual enrichment**: Document-level summaries prepended to chunks for better embeddings
- **Evaluation**: Pre-configured golden set and quality thresholds

## Quick Start

1. Install dependencies: `uv sync`
2. Index documents: `rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse`
3. Query: `rag-forge query "your question" --strategy hybrid --reranker cohere`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`

## Configuration

Edit `src/config.py` to customize your pipeline settings.
```

- [ ] **Step 3: Create src/config.py**

Create `templates/hybrid/project/src/config.py`:

```python
"""Pipeline configuration for the hybrid RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the hybrid RAG pipeline."""

    # Chunking
    chunk_strategy: str = "recursive"
    chunk_size: int = 512
    overlap_ratio: float = 0.1

    # Retrieval
    vector_db: str = "qdrant"
    embedding_model: str = "BAAI/bge-m3"
    retrieval_strategy: str = "hybrid"
    retrieval_alpha: float = 0.6
    top_k: int = 5

    # Reranking
    reranker: str = "cohere"
    cohere_model: str = "rerank-v3.5"

    # Enrichment
    enrich: bool = True
    enrichment_model: str = "claude-sonnet-4-20250514"

    # Generation
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024

    # Evaluation thresholds
    faithfulness_threshold: float = 0.85
    context_relevance_threshold: float = 0.80
```

- [ ] **Step 4: Create src/pipeline.py**

Create `templates/hybrid/project/src/pipeline.py`:

```python
"""Hybrid RAG pipeline: BM25 + vector search with reranking and enrichment."""

from pathlib import Path


def ingest(source_dir: str | Path, enrich: bool = True) -> int:
    """Ingest documents with hybrid indexing and optional enrichment.

    Returns chunk count. Run via CLI:
        rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse
    """
    # Generated by rag-forge init hybrid
    # Customize this pipeline to fit your use case
    print(f"Ingesting documents from {source_dir} (enrich={enrich})...")
    return 0


def query(question: str, top_k: int = 5, alpha: float = 0.6) -> str:
    """Query with hybrid retrieval (dense + BM25 + reranking).

    Run via CLI:
        rag-forge query "your question" --strategy hybrid --alpha 0.6 --reranker cohere
    """
    # Generated by rag-forge init hybrid
    print(f"Querying: {question} (top_k={top_k}, alpha={alpha})")
    return "Pipeline not yet configured. Run: rag-forge index --source ./docs --enrich"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        answer = query(" ".join(sys.argv[1:]))
        print(answer)
    else:
        print("Usage: python pipeline.py <your question>")
```

- [ ] **Step 5: Create eval/config.yaml**

Create `templates/hybrid/project/eval/config.yaml`:

```yaml
# RAG-Forge Evaluation Configuration
# Generated by: rag-forge init hybrid

metrics:
  - context_relevance
  - faithfulness
  - answer_relevance
  - hallucination

thresholds:
  context_relevance: 0.80
  faithfulness: 0.85
  answer_relevance: 0.80
  hallucination_rate: 0.05

ci_gate:
  metric: faithfulness
  threshold: 0.85
  block_on_failure: true

golden_set: eval/golden_set.json
```

- [ ] **Step 6: Create eval/golden_set.json**

Create `templates/hybrid/project/eval/golden_set.json`:

```json
[
  {
    "query": "What is the main topic of this document?",
    "expected_answer_keywords": ["topic", "document"],
    "difficulty": "easy",
    "topic": "general"
  },
  {
    "query": "What are the key concepts discussed?",
    "expected_answer_keywords": ["concepts", "key"],
    "difficulty": "medium",
    "topic": "general"
  }
]
```

- [ ] **Step 7: Update templates/hybrid/README.md**

Replace the full contents of `templates/hybrid/README.md`:

```markdown
# Hybrid RAG Template

Production-ready document Q&A with hybrid retrieval (BM25 + vector), Cohere reranking, contextual enrichment, and full evaluation suite.

Use: `rag-forge init hybrid`
```

- [ ] **Step 8: Commit**

```bash
git add templates/hybrid/
git commit -m "feat(templates): add hybrid template with BM25 + reranking + enrichment"
```

---

## Task 8: Enterprise Template

**Files:**
- Create: `templates/enterprise/project/` (7 files)
- Modify: `templates/enterprise/README.md`

- [ ] **Step 1: Create pyproject.toml**

Create `templates/enterprise/project/pyproject.toml`:

```toml
[project]
name = "my-rag-pipeline"
version = "0.1.0"
description = "An enterprise RAG pipeline with hybrid search, security guards, and CI/CD gates"
requires-python = ">=3.11"
dependencies = [
    "rag-forge-core[cohere]",
    "rag-forge-evaluator",
    "qdrant-client>=1.9",
    "sentence-transformers>=3.0",
]

[tool.rag-forge]
template = "enterprise"
chunk_strategy = "recursive"
chunk_size = 512
overlap_ratio = 0.1
vector_db = "qdrant"
embedding_model = "BAAI/bge-m3"
retrieval_strategy = "hybrid"
retrieval_alpha = 0.6
reranker = "cohere"
enrich = true
input_guard = true
output_guard = true
```

- [ ] **Step 2: Create README.md**

Create `templates/enterprise/project/README.md`:

```markdown
# Enterprise RAG Pipeline

A production-grade RAG pipeline with hybrid retrieval, security guards (InputGuard + OutputGuard), and CI/CD quality gates. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Hybrid search**: BM25 sparse + dense vector retrieval with Reciprocal Rank Fusion
- **Reranking**: Cohere Rerank API for improved precision
- **Security**: InputGuard (prompt injection, PII, rate limiting) + OutputGuard (faithfulness, PII, citations)
- **CI/CD gate**: GitHub Actions workflow that blocks merges when faithfulness drops below threshold
- **Evaluation**: Pre-configured golden set, quality thresholds, and audit reports

## Quick Start

1. Install dependencies: `uv sync`
2. Index documents: `rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse`
3. Query with guards: `rag-forge query "your question" --strategy hybrid --input-guard --output-guard`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`

## CI/CD

The included `.github/workflows/rag-audit.yml` runs evaluation on every PR and blocks merge if quality drops.

## Configuration

Edit `src/config.py` to customize your pipeline and security settings.
```

- [ ] **Step 3: Create src/config.py**

Create `templates/enterprise/project/src/config.py`:

```python
"""Pipeline configuration for the enterprise RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the enterprise RAG pipeline."""

    # Chunking
    chunk_strategy: str = "recursive"
    chunk_size: int = 512
    overlap_ratio: float = 0.1

    # Retrieval
    vector_db: str = "qdrant"
    embedding_model: str = "BAAI/bge-m3"
    retrieval_strategy: str = "hybrid"
    retrieval_alpha: float = 0.6
    top_k: int = 5

    # Reranking
    reranker: str = "cohere"
    cohere_model: str = "rerank-v3.5"

    # Enrichment
    enrich: bool = True
    enrichment_model: str = "claude-sonnet-4-20250514"

    # Security
    input_guard: bool = True
    output_guard: bool = True
    faithfulness_threshold: float = 0.85
    rate_limit_per_minute: int = 60

    # Generation
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024

    # Evaluation thresholds
    context_relevance_threshold: float = 0.80
```

- [ ] **Step 4: Create src/pipeline.py**

Create `templates/enterprise/project/src/pipeline.py`:

```python
"""Enterprise RAG pipeline: hybrid search + security guards + CI/CD gates."""

from pathlib import Path


def ingest(source_dir: str | Path, enrich: bool = True) -> int:
    """Ingest documents with hybrid indexing and enrichment.

    Returns chunk count. Run via CLI:
        rag-forge index --source ./docs --enrich --sparse-index-path .rag-forge/sparse
    """
    # Generated by rag-forge init enterprise
    # Customize this pipeline to fit your use case
    print(f"Ingesting documents from {source_dir} (enrich={enrich})...")
    return 0


def query(question: str, top_k: int = 5, alpha: float = 0.6) -> str:
    """Query with hybrid retrieval and security guards.

    Run via CLI:
        rag-forge query "your question" --strategy hybrid --input-guard --output-guard
    """
    # Generated by rag-forge init enterprise
    print(f"Querying: {question} (top_k={top_k}, alpha={alpha})")
    return "Pipeline not yet configured. Run: rag-forge index --source ./docs --enrich"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        answer = query(" ".join(sys.argv[1:]))
        print(answer)
    else:
        print("Usage: python pipeline.py <your question>")
```

- [ ] **Step 5: Create eval/config.yaml**

Create `templates/enterprise/project/eval/config.yaml`:

```yaml
# RAG-Forge Evaluation Configuration
# Generated by: rag-forge init enterprise

metrics:
  - context_relevance
  - faithfulness
  - answer_relevance
  - hallucination

thresholds:
  context_relevance: 0.80
  faithfulness: 0.85
  answer_relevance: 0.80
  hallucination_rate: 0.05

ci_gate:
  metric: faithfulness
  threshold: 0.85
  block_on_failure: true

golden_set: eval/golden_set.json
```

- [ ] **Step 6: Create eval/golden_set.json**

Create `templates/enterprise/project/eval/golden_set.json`:

```json
[
  {
    "query": "What is the main topic of this document?",
    "expected_answer_keywords": ["topic", "document"],
    "difficulty": "easy",
    "topic": "general"
  },
  {
    "query": "What are the key concepts discussed?",
    "expected_answer_keywords": ["concepts", "key"],
    "difficulty": "medium",
    "topic": "general"
  }
]
```

- [ ] **Step 7: Create .github/workflows/rag-audit.yml**

Create `templates/enterprise/project/.github/workflows/rag-audit.yml`:

```yaml
name: RAG Audit Gate

on:
  pull_request:
    branches: [main]
    paths:
      - "src/**"
      - "eval/**"

jobs:
  audit:
    name: RAG Quality Gate
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install 3.11
      - run: uv sync

      - name: Run RAG Audit
        run: |
          uv run python -m rag_forge_evaluator.cli audit \
            --golden-set eval/golden_set.json \
            --judge mock \
            --output ./reports

      - name: Check faithfulness gate
        run: |
          SCORE=$(jq -r '.metrics.faithfulness.score' reports/audit-report.json)
          THRESHOLD="0.85"
          echo "Faithfulness: ${SCORE} (threshold: ${THRESHOLD})"
          if (( $(echo "$SCORE < $THRESHOLD" | bc -l) )); then
            echo "::error::Faithfulness score (${SCORE}) below threshold (${THRESHOLD})"
            exit 1
          fi

      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: rag-audit-report
          path: reports/
```

- [ ] **Step 8: Update templates/enterprise/README.md**

Replace the full contents of `templates/enterprise/README.md`:

```markdown
# Enterprise RAG Template

Regulated industries and multi-tenant deployments with full security suite (PII, guardrails), CI/CD gates, and cost tracking.

Use: `rag-forge init enterprise`
```

- [ ] **Step 9: Commit**

```bash
git add templates/enterprise/
git commit -m "feat(templates): add enterprise template with security guards and CI gate"
```

---

## Task 9: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `cd packages/core && uv run pytest -v`
Expected: All tests pass.

Run: `cd packages/evaluator && uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run Python lint and type check**

Run: `uv run ruff check .`
Expected: No errors.

Run: `uv run mypy packages/core/src packages/evaluator/src`
Expected: No errors.

- [ ] **Step 3: Build all TypeScript packages**

Run: `pnpm run build`
Expected: All packages build successfully (shared, cli, mcp).

- [ ] **Step 4: Run TypeScript lint and typecheck**

Run: `pnpm run lint`
Expected: No errors.

Run: `pnpm run typecheck`
Expected: No errors.

- [ ] **Step 5: Fix any issues, commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 2D implementation"
```

- [ ] **Step 6: Push**

```bash
git push
```
