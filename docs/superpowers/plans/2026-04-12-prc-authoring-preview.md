# PR C: Authoring & Preview Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `rag-forge add <module>`, `rag-forge parse --preview`, `rag-forge chunk --preview`, and `rag-forge n8n export` — the pipeline authoring and preview commands.

**Architecture:** `add` copies module source files from a module registry into the user's project (shadcn/ui model). `parse` and `chunk` are preview-only commands that show what would happen without indexing. `n8n export` generates an importable n8n workflow JSON from pipeline config.

**Tech Stack:** Python 3.11+, pytest, TypeScript (Commander.js, fs/path for file copying)

**Branch:** `feat/prc-authoring-preview`

---

### Task 1: Parse Preview Command

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py` (add `parse` subcommand)
- Create: `packages/core/tests/test_parse_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/core/tests/test_parse_cli.py
"""Tests for parse preview CLI command."""

import json
from pathlib import Path

from rag_forge_core.parsing.directory import DirectoryParser


class TestParsePreview:
    def test_parse_directory_with_files(self, tmp_path: Path) -> None:
        (tmp_path / "doc1.md").write_text("# Hello\n\nWorld")
        (tmp_path / "doc2.txt").write_text("Plain text content")

        parser = DirectoryParser()
        results = parser.parse(str(tmp_path))
        assert len(results) >= 2

    def test_parse_empty_directory(self, tmp_path: Path) -> None:
        parser = DirectoryParser()
        results = parser.parse(str(tmp_path))
        assert len(results) == 0
```

- [ ] **Step 2: Add `cmd_parse` to core CLI**

```python
def cmd_parse(args: argparse.Namespace) -> None:
    """Preview document extraction without indexing."""
    try:
        source = Path(args.source)
        if not source.exists():
            json.dump({"success": False, "error": f"Source directory not found: {source}"}, sys.stdout)
            sys.exit(1)

        parser = DirectoryParser()
        documents = parser.parse(str(source))

        files_info = []
        for doc in documents:
            files_info.append({
                "path": doc.source,
                "type": doc.file_type if hasattr(doc, "file_type") else "unknown",
                "characters": len(doc.text),
            })

        output = {
            "success": True,
            "files_found": len(documents),
            "files": files_info,
            "total_characters": sum(f["characters"] for f in files_info),
        }
    except Exception as e:
        output = {"success": False, "error": str(e)}

    json.dump(output, sys.stdout)
```

Add subparser:
```python
    parse_parser = subparsers.add_parser("parse", help="Preview document extraction")
    parse_parser.add_argument("--source", required=True, help="Source directory")
```

- [ ] **Step 3: Run tests, commit**

```bash
git add packages/core/src/rag_forge_core/cli.py packages/core/tests/test_parse_cli.py
git commit -m "feat(cli): add parse preview command"
```

---

### Task 2: Chunk Preview Command

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py` (add `chunk` subcommand)

- [ ] **Step 1: Add `cmd_chunk` to core CLI**

```python
def cmd_chunk(args: argparse.Namespace) -> None:
    """Preview chunking without indexing."""
    try:
        source = Path(args.source)
        if not source.exists():
            json.dump({"success": False, "error": f"Source directory not found: {source}"}, sys.stdout)
            sys.exit(1)

        from rag_forge_core.chunking.config import ChunkConfig
        from rag_forge_core.chunking.factory import create_chunker
        from rag_forge_core.parsing.directory import DirectoryParser

        strategy = args.strategy or "recursive"
        chunk_size = int(args.chunk_size) if args.chunk_size else 512

        chunk_config = ChunkConfig(strategy=strategy, chunk_size=chunk_size)
        chunker = create_chunker(config=chunk_config)
        parser = DirectoryParser()

        documents = parser.parse(str(source))
        all_chunks = []
        for doc in documents:
            chunks = chunker.chunk(doc.text, doc.source)
            all_chunks.extend(chunks)

        stats = chunker.stats(all_chunks) if all_chunks else None

        # Sample first 3 chunk boundaries
        samples = []
        for chunk in all_chunks[:3]:
            samples.append({
                "index": chunk.chunk_index,
                "source": chunk.source_document,
                "preview": chunk.text[:100] + ("..." if len(chunk.text) > 100 else ""),
            })

        output = {
            "success": True,
            "strategy": strategy,
            "chunk_size": chunk_size,
            "total_chunks": len(all_chunks),
            "stats": {
                "avg_chunk_size": stats.avg_chunk_size if stats else 0,
                "min_chunk_size": stats.min_chunk_size if stats else 0,
                "max_chunk_size": stats.max_chunk_size if stats else 0,
                "total_tokens": stats.total_tokens if stats else 0,
            },
            "samples": samples,
        }
    except Exception as e:
        output = {"success": False, "error": str(e)}

    json.dump(output, sys.stdout)
```

Add subparser:
```python
    chunk_parser = subparsers.add_parser("chunk", help="Preview chunking")
    chunk_parser.add_argument("--source", required=True, help="Source directory")
    chunk_parser.add_argument("--strategy", default="recursive", help="Chunking strategy")
    chunk_parser.add_argument("--chunk-size", help="Target chunk size in tokens")
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(cli): add chunk preview command"
```

---

### Task 3: n8n Export

**Files:**
- Create: `packages/core/src/rag_forge_core/n8n_export.py`
- Create: `packages/core/tests/test_n8n_export.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/core/tests/test_n8n_export.py
"""Tests for n8n workflow export."""

import json
from pathlib import Path

from rag_forge_core.n8n_export import generate_n8n_workflow


class TestN8NExport:
    def test_generates_valid_json(self) -> None:
        workflow = generate_n8n_workflow(mcp_url="http://localhost:3100/sse")
        assert isinstance(workflow, dict)
        assert "nodes" in workflow
        assert "connections" in workflow

    def test_contains_webhook_trigger(self) -> None:
        workflow = generate_n8n_workflow(mcp_url="http://localhost:3100/sse")
        node_types = [n["type"] for n in workflow["nodes"]]
        assert any("webhook" in t.lower() for t in node_types)

    def test_contains_mcp_url(self) -> None:
        url = "http://my-server:3100/sse"
        workflow = generate_n8n_workflow(mcp_url=url)
        workflow_str = json.dumps(workflow)
        assert url in workflow_str

    def test_saves_to_file(self, tmp_path: Path) -> None:
        output = tmp_path / "workflow.json"
        workflow = generate_n8n_workflow(mcp_url="http://localhost:3100/sse")
        output.write_text(json.dumps(workflow, indent=2))
        assert output.exists()
        loaded = json.loads(output.read_text())
        assert "nodes" in loaded
```

- [ ] **Step 2: Implement n8n export**

```python
# packages/core/src/rag_forge_core/n8n_export.py
"""Generate importable n8n workflow JSON from pipeline configuration.

Creates a workflow with: Webhook trigger -> AI Agent (MCP) -> HTTP Response.
The MCP node connects to the project's rag-forge MCP server.
"""

from typing import Any


def generate_n8n_workflow(
    mcp_url: str = "http://localhost:3100/sse",
    workflow_name: str = "RAG-Forge Pipeline",
) -> dict[str, Any]:
    """Generate an n8n workflow JSON connecting to a RAG-Forge MCP server."""
    return {
        "name": workflow_name,
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "rag-query",
                    "responseMode": "responseNode",
                },
                "id": "webhook-trigger",
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [250, 300],
            },
            {
                "parameters": {
                    "agent": "conversationalAgent",
                    "options": {
                        "systemMessage": (
                            "You are a RAG assistant. Use the rag_query tool to answer "
                            "questions based on the indexed document collection."
                        ),
                    },
                },
                "id": "ai-agent",
                "name": "AI Agent",
                "type": "@n8n/n8n-nodes-langchain.agent",
                "typeVersion": 1.7,
                "position": [470, 300],
            },
            {
                "parameters": {
                    "sseEndpoint": mcp_url,
                },
                "id": "mcp-tool",
                "name": "RAG-Forge MCP",
                "type": "@n8n/n8n-nodes-langchain.toolMcp",
                "typeVersion": 1,
                "position": [470, 500],
            },
            {
                "parameters": {
                    "respondWith": "text",
                    "responseBody": "={{ $json.output }}",
                },
                "id": "http-response",
                "name": "HTTP Response",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1,
                "position": [690, 300],
            },
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [
                    [{"node": "AI Agent", "type": "main", "index": 0}],
                ],
            },
            "AI Agent": {
                "main": [
                    [{"node": "HTTP Response", "type": "main", "index": 0}],
                ],
            },
            "RAG-Forge MCP": {
                "ai_tool": [
                    [{"node": "AI Agent", "type": "ai_tool", "index": 0}],
                ],
            },
        },
        "settings": {
            "executionOrder": "v1",
        },
    }
```

- [ ] **Step 3: Add `cmd_n8n_export` to core CLI**

- [ ] **Step 4: Run tests, commit**

```bash
git add packages/core/src/rag_forge_core/n8n_export.py packages/core/tests/test_n8n_export.py packages/core/src/rag_forge_core/cli.py
git commit -m "feat(cli): add n8n workflow export command"
```

---

### Task 4: Module Add Command

**Files:**
- Create: `packages/cli/src/modules/manifest.json`
- Create: `packages/cli/src/commands/add.ts`
- Modify: `packages/cli/src/index.ts`

- [ ] **Step 1: Create module manifest**

```json
{
  "modules": {
    "guardrails": {
      "description": "InputGuard + OutputGuard security pipeline",
      "files": [
        {"src": "security/input_guard.py", "dest": "src/security/input_guard.py"},
        {"src": "security/output_guard.py", "dest": "src/security/output_guard.py"},
        {"src": "security/injection.py", "dest": "src/security/injection.py"},
        {"src": "security/pii.py", "dest": "src/security/pii.py"},
        {"src": "security/faithfulness.py", "dest": "src/security/faithfulness.py"},
        {"src": "security/citations.py", "dest": "src/security/citations.py"}
      ],
      "dependencies": ["presidio-analyzer>=2.2"]
    },
    "caching": {
      "description": "Semantic query caching with Redis support",
      "files": [
        {"src": "context/semantic_cache.py", "dest": "src/caching/semantic_cache.py"},
        {"src": "context/cache_store.py", "dest": "src/caching/cache_store.py"}
      ],
      "dependencies": ["redis>=5.0"]
    },
    "reranking": {
      "description": "Cross-encoder reranking (Cohere + BGE local)",
      "files": [
        {"src": "retrieval/reranker.py", "dest": "src/retrieval/reranker.py"}
      ],
      "dependencies": ["cohere>=5.0"]
    },
    "enrichment": {
      "description": "Contextual enrichment (document summary prepending)",
      "files": [
        {"src": "context/enricher.py", "dest": "src/enrichment/enricher.py"}
      ],
      "dependencies": []
    },
    "observability": {
      "description": "OpenTelemetry tracing for all pipeline stages",
      "files": [
        {"src": "observability/tracing.py", "dest": "src/observability/tracing.py"}
      ],
      "dependencies": ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
    },
    "hybrid-retrieval": {
      "description": "Hybrid dense+sparse retrieval with RRF fusion",
      "files": [
        {"src": "retrieval/sparse.py", "dest": "src/retrieval/sparse.py"},
        {"src": "retrieval/hybrid.py", "dest": "src/retrieval/hybrid.py"}
      ],
      "dependencies": ["bm25s>=0.2"]
    }
  }
}
```

- [ ] **Step 2: Create add.ts**

The `add` command reads the manifest, looks up the requested module, copies files from the enterprise template (which has all features) into the user's project directory.

```typescript
// packages/cli/src/commands/add.ts
import { existsSync, readFileSync } from "node:fs";
import { cp, mkdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";

interface ModuleManifest {
  modules: Record<string, {
    description: string;
    files: Array<{ src: string; dest: string }>;
    dependencies: string[];
  }>;
}

function getManifestPath(): string {
  const currentDir = fileURLToPath(new URL(".", import.meta.url));
  return resolve(currentDir, "..", "modules", "manifest.json");
}

function getTemplateSourceDir(): string {
  const currentDir = fileURLToPath(new URL(".", import.meta.url));
  return resolve(currentDir, "..", "..", "..", "..", "templates", "enterprise", "project", "src");
}

export function registerAddCommand(program: Command): void {
  program
    .command("add")
    .argument("<module>", "Module to add: guardrails | caching | reranking | enrichment | observability | hybrid-retrieval")
    .description("Add a feature module as editable source code (shadcn/ui model)")
    .action(async (moduleName: string) => {
      const manifestPath = getManifestPath();
      if (!existsSync(manifestPath)) {
        logger.error("Module manifest not found");
        process.exit(1);
      }

      const manifest: ModuleManifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
      const mod = manifest.modules[moduleName];

      if (!mod) {
        const available = Object.keys(manifest.modules).join(", ");
        logger.error(`Unknown module: ${moduleName}. Available: ${available}`);
        process.exit(1);
      }

      logger.info(`Adding module: ${moduleName} — ${mod.description}`);

      const sourceDir = getTemplateSourceDir();
      let added = 0;
      let skipped = 0;

      for (const file of mod.files) {
        const srcPath = resolve(sourceDir, file.src);
        const destPath = resolve(process.cwd(), file.dest);

        if (existsSync(destPath)) {
          logger.warn(`  Skip (exists): ${file.dest}`);
          skipped++;
          continue;
        }

        if (!existsSync(srcPath)) {
          logger.warn(`  Skip (source not found): ${file.src}`);
          skipped++;
          continue;
        }

        await mkdir(dirname(destPath), { recursive: true });
        await cp(srcPath, destPath);
        logger.success(`  Added: ${file.dest}`);
        added++;
      }

      logger.info(`\nAdded ${String(added)} files, skipped ${String(skipped)}`);

      if (mod.dependencies.length > 0) {
        logger.info(`\nInstall dependencies:`);
        logger.info(`  pip install ${mod.dependencies.join(" ")}`);
      }
    });
}
```

- [ ] **Step 3: Register in index.ts**

- [ ] **Step 4: TypeScript check + commit**

```bash
git add packages/cli/src/modules/manifest.json packages/cli/src/commands/add.ts packages/cli/src/index.ts
git commit -m "feat(cli): add module add command (shadcn/ui pattern)"
```

---

### Task 5: TypeScript CLI Commands (parse, chunk, n8n export)

**Files:**
- Create: `packages/cli/src/commands/parse.ts`
- Create: `packages/cli/src/commands/chunk.ts`
- Create: `packages/cli/src/commands/n8n.ts`
- Modify: `packages/cli/src/index.ts`

- [ ] **Step 1: Create all three TS command files**

Each follows the established pattern:
- `parse.ts`: calls `rag_forge_core.cli parse --source <dir>`, displays file list and character counts
- `chunk.ts`: calls `rag_forge_core.cli chunk --source <dir> --strategy <name>`, displays stats and samples
- `n8n.ts`: calls `rag_forge_core.cli n8n-export --output <file> --mcp-url <url>`, displays output path

- [ ] **Step 2: Register in index.ts**

- [ ] **Step 3: TypeScript check + lint + commit**

```bash
git add packages/cli/src/commands/parse.ts packages/cli/src/commands/chunk.ts packages/cli/src/commands/n8n.ts packages/cli/src/index.ts
git commit -m "feat(cli): add parse, chunk, n8n export TypeScript commands"
```

---

### Task 6: Push and Open PR

- [ ] **Step 1: Full build quality check**
- [ ] **Step 2: Push and create PR**

```bash
git push -u origin feat/prc-authoring-preview
gh pr create --title "feat: add module add, parse, chunk preview, n8n export commands" --body "..."
```
