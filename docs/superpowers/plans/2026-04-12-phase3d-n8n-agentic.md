# Phase 3D: n8n Integration + Agentic Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add HTTP/SSE transport to the MCP server for n8n integration, implement multi-query decomposition for complex questions (AgenticQueryEngine), and build the n8n and agentic project templates.

**Architecture:** The MCP server gains an HTTP transport via `@modelcontextprotocol/sdk`'s SSE support, selected by `--transport http`. The `AgenticQueryEngine` wraps the existing retriever to decompose queries via LLM, retrieve per sub-query, merge results, and generate a combined answer. Templates are static project scaffolds.

**Tech Stack:** TypeScript (@modelcontextprotocol/sdk SSE transport, Node HTTP), Python 3.11+ (json, opentelemetry).

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/mcp/src/transports/http.ts` | HTTP/SSE MCP transport server |
| `packages/core/src/rag_forge_core/query/agentic.py` | AgenticQueryEngine with multi-query decomposition |
| `packages/core/tests/test_agentic_query.py` | Agentic engine tests |
| `templates/n8n/project/workflow.json` | n8n workflow JSON |
| `templates/n8n/project/README.md` | n8n setup guide |
| `templates/n8n/project/.env.example` | Environment variables template |
| `templates/agentic/project/pyproject.toml` | Agentic template package config |
| `templates/agentic/project/README.md` | Agentic template docs |
| `templates/agentic/project/src/config.py` | Agentic pipeline config |
| `templates/agentic/project/src/pipeline.py` | Agentic pipeline example |
| `templates/agentic/project/eval/config.yaml` | Agentic eval config |
| `templates/agentic/project/eval/golden_set.json` | Agentic golden set |

### Modified Files

| File | Change |
|------|--------|
| `packages/mcp/src/main.ts` | Transport selection (stdio vs http) |
| `packages/mcp/tsup.config.ts` | Add transports directory to build |
| `packages/cli/src/commands/serve.ts` | Add --transport and --port flags |
| `packages/core/src/rag_forge_core/cli.py` | Add --agent-mode flag |
| `packages/cli/src/commands/query.ts` | Add --agent-mode flag |
| `templates/n8n/README.md` | Replace stub |
| `templates/agentic/README.md` | Replace stub |

---

## Task 1: HTTP/SSE Transport

**Files:**
- Create: `packages/mcp/src/transports/http.ts`
- Modify: `packages/mcp/src/main.ts`
- Modify: `packages/mcp/tsup.config.ts`

- [ ] **Step 1: Create the HTTP transport**

Create `packages/mcp/src/transports/http.ts`:

```typescript
import { createServer as createHttpServer } from "node:http";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer } from "../index.js";

export async function startHttpServer(port: number): Promise<void> {
  const mcpServer = createServer();
  let transport: SSEServerTransport | null = null;

  const httpServer = createHttpServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/sse") {
      transport = new SSEServerTransport("/messages", res);
      await mcpServer.connect(transport);
    } else if (req.method === "POST" && req.url === "/messages") {
      if (transport === null) {
        res.writeHead(400);
        res.end("No active SSE connection");
        return;
      }
      await transport.handlePostMessage(req, res);
    } else if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", tools: 5 }));
    } else {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  httpServer.listen(port, () => {
    console.error(`RAG-Forge MCP server listening on http://localhost:${String(port)}/sse`);
  });

  await new Promise<never>(() => {});
}
```

NOTE: The `SSEServerTransport` API may differ based on the installed `@modelcontextprotocol/sdk` version. The implementer should check the actual SDK exports. If `SSEServerTransport` is not available at that path, check for alternative imports like `@modelcontextprotocol/sdk/server/sse` or `@modelcontextprotocol/sdk/sse`. Adapt the import and usage accordingly. The core pattern is: create HTTP server, handle GET `/sse` for event stream, handle POST `/messages` for client messages.

- [ ] **Step 2: Update main.ts for transport selection**

Replace the full contents of `packages/mcp/src/main.ts`:

```typescript
import { startServer } from "./server.js";

const args = process.argv.slice(2);
const transportIdx = args.indexOf("--transport");
const transport = transportIdx >= 0 && args[transportIdx + 1] ? args[transportIdx + 1] : "stdio";
const portIdx = args.indexOf("--port");
const port = portIdx >= 0 && args[portIdx + 1] ? parseInt(args[portIdx + 1], 10) : 3100;

async function main(): Promise<void> {
  if (transport === "http") {
    const { startHttpServer } = await import("./transports/http.js");
    await startHttpServer(port);
  } else {
    await startServer();
  }
}

main().catch((error: unknown) => {
  console.error("MCP server failed to start:", error);
  process.exit(1);
});
```

- [ ] **Step 3: Update tsup.config.ts**

Replace the full contents of `packages/mcp/tsup.config.ts`:

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

Note: tsup will automatically bundle the transports directory since it's imported by main.ts.

- [ ] **Step 4: Build and verify**

Run: `cd packages/mcp && pnpm run build && pnpm run typecheck`
Expected: Build succeeds with `dist/main.js` containing the transport selection logic.

- [ ] **Step 5: Commit**

```bash
git add packages/mcp/src/transports/http.ts packages/mcp/src/main.ts packages/mcp/tsup.config.ts
git commit -m "feat(mcp): add HTTP/SSE transport for n8n integration"
```

---

## Task 2: Update serve Command

**Files:**
- Modify: `packages/cli/src/commands/serve.ts`

- [ ] **Step 1: Add transport and port flags**

Replace the full contents of `packages/cli/src/commands/serve.ts`:

```typescript
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Command } from "commander";
import { logger } from "../lib/logger.js";

function getMcpMainPath(): string {
  const currentDir = fileURLToPath(new URL(".", import.meta.url));
  return resolve(currentDir, "..", "..", "..", "mcp", "dist", "main.js");
}

export function registerServeCommand(program: Command): void {
  program
    .command("serve")
    .option("--mcp", "Launch MCP server")
    .option("--transport <type>", "Transport: stdio | http", "stdio")
    .option("-p, --port <number>", "Port for HTTP transport", "3100")
    .description("Start the RAG-Forge server")
    .action(async (options: { mcp?: boolean; transport: string; port: string }) => {
      if (!options.mcp) {
        logger.error("Please specify a server mode. Currently supported: --mcp");
        process.exit(1);
      }

      const mcpMain = getMcpMainPath();

      if (!existsSync(mcpMain)) {
        logger.error(`MCP server not found at ${mcpMain}. Run 'pnpm run build' first.`);
        process.exit(1);
      }

      const args = [mcpMain];
      if (options.transport === "http") {
        args.push("--transport", "http", "--port", options.port);
        logger.info(`Starting MCP server on http://localhost:${options.port}/sse`);
      } else {
        logger.info("Starting MCP server on stdio...");
      }

      const child = spawn(process.execPath, args, {
        stdio: "inherit",
      });

      child.on("error", (error) => {
        logger.error(`MCP server failed: ${error.message}`);
        process.exit(1);
      });

      child.on("exit", (code) => {
        process.exit(code ?? 0);
      });
    });
}
```

- [ ] **Step 2: Build and verify**

Run: `cd packages/cli && pnpm run build && pnpm run typecheck`
Expected: Both succeed.

- [ ] **Step 3: Commit**

```bash
git add packages/cli/src/commands/serve.ts
git commit -m "feat(cli): add --transport and --port flags to serve command"
```

---

## Task 3: AgenticQueryEngine

**Files:**
- Create: `packages/core/src/rag_forge_core/query/agentic.py`
- Test: `packages/core/tests/test_agentic_query.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_agentic_query.py`:

```python
"""Tests for AgenticQueryEngine with multi-query decomposition."""

import json
import tempfile
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.generation.mock_generator import MockGenerator
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.query.agentic import AgenticQueryEngine
from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.dense import DenseRetriever
from rag_forge_core.storage.qdrant import QdrantStore


def _setup_engine() -> tuple[AgenticQueryEngine, MockEmbedder, QdrantStore]:
    with tempfile.TemporaryDirectory() as tmpdir:
        docs = Path(tmpdir) / "docs"
        docs.mkdir()
        (docs / "python.md").write_text("# Python\n\nPython is used for data science and web development.", encoding="utf-8")
        (docs / "rust.md").write_text("# Rust\n\nRust is used for systems programming and performance.", encoding="utf-8")

        embedder = MockEmbedder(dimension=384)
        store = QdrantStore()
        IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
            embedder=embedder,
            store=store,
            collection_name="test-agentic",
        ).run(docs)

        retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-agentic")

        # Generator that returns valid JSON for decomposition
        decompose_response = json.dumps(["What is Python used for?", "What is Rust used for?"])
        generator = MockGenerator(fixed_response=decompose_response)

        engine = AgenticQueryEngine(
            retriever=retriever,
            generator=generator,
            top_k=5,
        )
        return engine, embedder, store


class TestAgenticQueryEngine:
    def test_returns_query_result(self) -> None:
        engine, _, _ = _setup_engine()
        result = engine.query("Compare Python and Rust")
        assert result is not None
        assert len(result.answer) > 0
        assert result.chunks_retrieved > 0

    def test_decomposition_produces_sub_queries(self) -> None:
        engine, _, _ = _setup_engine()
        sub_queries = engine._decompose("Compare Python and Rust for data science")
        assert isinstance(sub_queries, list)
        assert len(sub_queries) >= 1

    def test_invalid_decomposition_falls_back(self) -> None:
        """If LLM returns invalid JSON, fall back to original question."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = Path(tmpdir) / "docs"
            docs.mkdir()
            (docs / "test.md").write_text("# Test\n\nHello world.", encoding="utf-8")

            embedder = MockEmbedder(dimension=384)
            store = QdrantStore()
            IngestionPipeline(
                parser=DirectoryParser(),
                chunker=RecursiveChunker(ChunkConfig(strategy="recursive", chunk_size=128)),
                embedder=embedder,
                store=store,
                collection_name="test-fallback",
            ).run(docs)

            retriever = DenseRetriever(embedder=embedder, store=store, collection_name="test-fallback")
            # Generator returns non-JSON — decomposition should fall back
            engine = AgenticQueryEngine(
                retriever=retriever,
                generator=MockGenerator(),
                top_k=5,
            )
            sub_queries = engine._decompose("What is Python?")
            assert sub_queries == ["What is Python?"]

    def test_merge_deduplicates_by_chunk_id(self) -> None:
        engine, _, _ = _setup_engine()
        results1 = [
            RetrievalResult(chunk_id="c1", text="Python", score=0.9, source_document="doc.md"),
            RetrievalResult(chunk_id="c2", text="Rust", score=0.8, source_document="doc.md"),
        ]
        results2 = [
            RetrievalResult(chunk_id="c1", text="Python", score=0.7, source_document="doc.md"),
            RetrievalResult(chunk_id="c3", text="Java", score=0.6, source_document="doc.md"),
        ]
        merged = engine._merge_results([results1, results2])
        chunk_ids = [r.chunk_id for r in merged]
        assert len(chunk_ids) == len(set(chunk_ids))
        # c1 should keep the higher score (0.9)
        c1 = next(r for r in merged if r.chunk_id == "c1")
        assert c1.score == 0.9

    def test_merge_sorts_by_score_descending(self) -> None:
        engine, _, _ = _setup_engine()
        results = [
            [RetrievalResult(chunk_id="c1", text="A", score=0.5, source_document="d")],
            [RetrievalResult(chunk_id="c2", text="B", score=0.9, source_document="d")],
        ]
        merged = engine._merge_results(results)
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_agentic_query.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `packages/core/src/rag_forge_core/query/agentic.py`:

```python
"""Agentic query engine with multi-query decomposition.

Breaks complex queries into sub-questions via LLM, retrieves for each
independently, merges results, and generates a final answer.
"""

from __future__ import annotations

import json
import logging
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from rag_forge_core.retrieval.base import RetrievalResult
from rag_forge_core.retrieval.hybrid import HybridRetriever

if TYPE_CHECKING:
    from opentelemetry import trace

    from rag_forge_core.context.semantic_cache import SemanticCache
    from rag_forge_core.generation.base import GenerationProvider
    from rag_forge_core.query.engine import QueryResult
    from rag_forge_core.retrieval.base import RetrieverProtocol
    from rag_forge_core.security.input_guard import InputGuard
    from rag_forge_core.security.output_guard import OutputGuard

logger = logging.getLogger(__name__)

_DECOMPOSE_SYSTEM_PROMPT = (
    "You are a query decomposition assistant. Break the following complex "
    "question into 3-5 simpler, independent sub-questions that can each be "
    "answered by searching a document collection separately.\n\n"
    'Respond with ONLY a JSON array of strings: ["sub-question 1", "sub-question 2", ...]'
)

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on the "
    "provided context. If the context does not contain enough information to answer "
    "the question, say so clearly. Do not make up information."
)


class AgenticQueryEngine:
    """Multi-query decomposition engine for complex questions."""

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
        tracer: trace.Tracer | None = None,
        cache: SemanticCache | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._top_k = top_k
        self._input_guard = input_guard
        self._output_guard = output_guard
        self._tracer = tracer
        self._cache = cache

    def _span(self, name: str) -> Any:
        if self._tracer is not None:
            return self._tracer.start_as_current_span(name)
        return nullcontext()

    def query(self, question: str, user_id: str = "default") -> QueryResult:
        """Decompose, retrieve per sub-query, merge, generate."""
        from rag_forge_core.query.engine import QueryResult

        with self._span("rag-forge.agentic_query"):
            # 1. Input guard
            if self._input_guard is not None:
                guard_result = self._input_guard.check(question, user_id=user_id)
                if not guard_result.passed:
                    return QueryResult(
                        answer="",
                        sources=[],
                        model_used=self._generator.model_name(),
                        chunks_retrieved=0,
                        blocked=True,
                        blocked_reason=guard_result.reason,
                    )

            # 2. Cache check
            if self._cache is not None:
                cached = self._cache.get(question)
                if cached is not None:
                    return cached

            # 3. Decompose
            with self._span("rag-forge.decompose") as span:
                sub_queries = self._decompose(question)
                if span is not None:
                    span.set_attribute("sub_query_count", len(sub_queries))

            # 4. Retrieve for each sub-query
            all_results: list[list[RetrievalResult]] = []
            for sub_q in sub_queries:
                with self._span("rag-forge.sub_retrieve") as span:
                    results = self._retriever.retrieve(sub_q, self._top_k)
                    all_results.append(results)
                    if span is not None:
                        span.set_attribute("sub_query", sub_q)
                        span.set_attribute("result_count", len(results))

            # 5. Merge and deduplicate
            with self._span("rag-forge.merge"):
                merged = self._merge_results(all_results)

            if not merged:
                return QueryResult(
                    answer="No relevant context found for your question.",
                    sources=[],
                    model_used=self._generator.model_name(),
                    chunks_retrieved=0,
                )

            # 6. Generate final answer from merged context
            context_text = "\n\n".join(
                f"[Source {i + 1}]: {r.text}" for i, r in enumerate(merged)
            )
            user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"

            with self._span("rag-forge.generate") as span:
                answer = self._generator.generate(_SYSTEM_PROMPT, user_prompt)
                if span is not None:
                    span.set_attribute("model", self._generator.model_name())

            # 7. Output guard
            if self._output_guard is not None:
                chunk_ids = [r.chunk_id for r in merged]
                contexts = [r.text for r in merged]
                metadata_list = [dict(r.metadata) for r in merged]
                output_result = self._output_guard.check(
                    answer, contexts, chunk_ids=chunk_ids, contexts_metadata=metadata_list
                )
                if not output_result.passed:
                    return QueryResult(
                        answer="",
                        sources=[],
                        model_used=self._generator.model_name(),
                        chunks_retrieved=len(merged),
                        blocked=True,
                        blocked_reason=output_result.reason,
                    )

            result = QueryResult(
                answer=answer,
                sources=merged,
                model_used=self._generator.model_name(),
                chunks_retrieved=len(merged),
            )

            # 8. Cache store
            if self._cache is not None:
                self._cache.set(question, result)

            return result

    def _decompose(self, question: str) -> list[str]:
        """Break a complex question into simpler sub-questions via LLM."""
        try:
            response = self._generator.generate(_DECOMPOSE_SYSTEM_PROMPT, question)
            sub_queries = json.loads(response)
            if isinstance(sub_queries, list) and len(sub_queries) > 0:
                return [str(q) for q in sub_queries]
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Query decomposition returned invalid JSON, using original question")
        return [question]

    def _merge_results(
        self, results_per_query: list[list[RetrievalResult]]
    ) -> list[RetrievalResult]:
        """Merge and deduplicate retrieval results from multiple sub-queries."""
        best: dict[str, RetrievalResult] = {}
        for results in results_per_query:
            for result in results:
                existing = best.get(result.chunk_id)
                if existing is None or result.score > existing.score:
                    best[result.chunk_id] = result

        merged = sorted(best.values(), key=lambda r: r.score, reverse=True)
        return merged[: self._top_k * 2]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_agentic_query.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/query/agentic.py packages/core/tests/test_agentic_query.py
git commit -m "feat(core): add AgenticQueryEngine with multi-query decomposition"
```

---

## Task 4: CLI --agent-mode Flag

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`
- Modify: `packages/cli/src/commands/query.ts`

- [ ] **Step 1: Update Python CLI**

Read `packages/core/src/rag_forge_core/cli.py`. Add:

1. Import at top:
```python
from rag_forge_core.query.agentic import AgenticQueryEngine
```

2. Add arg to query parser in `main()`:
```python
    query_parser.add_argument(
        "--agent-mode", action="store_true",
        help="Enable multi-query decomposition for complex questions",
    )
```

3. In `cmd_query()`, after building the QueryEngine, check for agent mode:

Find the line where `engine = QueryEngine(...)` is constructed. AFTER it, add:

```python
    if args.agent_mode:
        engine = AgenticQueryEngine(
            retriever=retriever,
            generator=_create_generator(generator_provider),
            top_k=top_k,
            input_guard=input_guard,
            output_guard=output_guard,
            tracer=tracer,
            cache=cache,
        )
```

NOTE: The `engine` variable is reused — `AgenticQueryEngine.query()` returns the same `QueryResult` type, so the rest of `cmd_query()` works unchanged.

- [ ] **Step 2: Update TypeScript CLI**

Read `packages/cli/src/commands/query.ts`. Add option:
```typescript
    .option("--agent-mode", "Enable multi-query decomposition")
```

Add to options type: `agentMode?: boolean;`

Add to args forwarding:
```typescript
          if (options.agentMode) {
            args.push("--agent-mode");
          }
```

- [ ] **Step 3: Build and verify**

Run: `cd packages/cli && pnpm run build && pnpm run typecheck`
Run: `cd packages/core && uv run python -m rag_forge_core.cli query --help` — should show `--agent-mode`

- [ ] **Step 4: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py packages/cli/src/commands/query.ts
git commit -m "feat(cli): add --agent-mode flag for multi-query decomposition"
```

---

## Task 5: n8n Template

**Files:**
- Create: `templates/n8n/project/workflow.json`
- Create: `templates/n8n/project/README.md`
- Create: `templates/n8n/project/.env.example`
- Modify: `templates/n8n/README.md`

- [ ] **Step 1: Create workflow.json**

Create `templates/n8n/project/workflow.json`:

```json
{
  "name": "RAG-Forge AI Agent",
  "nodes": [
    {
      "parameters": {},
      "id": "trigger",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "agent": {
          "agentType": "toolsAgent"
        },
        "options": {
          "systemMessage": "You are a helpful RAG assistant. Use the available tools to search documents and answer questions."
        }
      },
      "id": "agent",
      "name": "AI Agent",
      "type": "@n8n/n8n-nodes-langchain.agent",
      "typeVersion": 1,
      "position": [500, 300]
    },
    {
      "parameters": {
        "sseEndpoint": "={{ $env.RAG_FORGE_MCP_URL || 'http://localhost:3100/sse' }}"
      },
      "id": "mcp",
      "name": "RAG-Forge MCP",
      "type": "@n8n/n8n-nodes-langchain.toolMcp",
      "typeVersion": 1,
      "position": [500, 500]
    }
  ],
  "connections": {
    "Manual Trigger": {
      "main": [
        [{ "node": "AI Agent", "type": "main", "index": 0 }]
      ]
    },
    "RAG-Forge MCP": {
      "ai_tool": [
        [{ "node": "AI Agent", "type": "ai_tool", "index": 0 }]
      ]
    }
  }
}
```

NOTE: The exact n8n node types and schema may vary based on n8n version. This is a starting-point workflow that users will import and adjust. The key configuration is the MCP SSE endpoint URL.

- [ ] **Step 2: Create README.md**

Create `templates/n8n/project/README.md`:

```markdown
# RAG-Forge n8n Integration

Connect n8n's AI Agent to RAG-Forge via MCP (Model Context Protocol) for automated document Q&A, ingestion, and evaluation.

## Prerequisites

- [n8n](https://n8n.io/) installed (self-hosted or cloud)
- RAG-Forge installed with documents indexed
- API keys set as environment variables

## Setup

### 1. Start RAG-Forge MCP Server

```bash
rag-forge serve --mcp --transport http --port 3100
```

### 2. Import Workflow

1. Open n8n
2. Go to Workflows → Import from File
3. Select `workflow.json` from this directory
4. The workflow includes a Manual Trigger → AI Agent → RAG-Forge MCP connection

### 3. Configure

- Set `RAG_FORGE_MCP_URL` environment variable in n8n (default: `http://localhost:3100/sse`)
- Configure your LLM provider in the AI Agent node (OpenAI, Anthropic, etc.)

### 4. Run

Click "Execute Workflow" in n8n. The AI Agent can now:
- **rag_query** — Ask questions against your indexed documents
- **rag_audit** — Run evaluation audits
- **rag_ingest** — Index new documents
- **rag_inspect** — Debug specific chunks
- **rag_status** — Check pipeline health

## Available MCP Tools

| Tool | Description |
|------|------------|
| `rag_query` | Execute a RAG query with optional hybrid retrieval |
| `rag_audit` | Run evaluation and generate audit report |
| `rag_ingest` | Index documents from a directory |
| `rag_inspect` | Look up a chunk by ID |
| `rag_status` | Check pipeline health and chunk count |

## Extending

- Add a **Webhook Trigger** to auto-ingest documents when new files arrive
- Add a **Schedule Trigger** to run periodic audits
- Chain multiple AI Agent nodes for complex workflows
```

- [ ] **Step 3: Create .env.example**

Create `templates/n8n/project/.env.example`:

```
# RAG-Forge MCP Server URL
RAG_FORGE_MCP_URL=http://localhost:3100/sse

# LLM API Keys (configure in n8n credentials)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 4: Update root README**

Replace `templates/n8n/README.md`:

```markdown
# n8n Integration Template

AI automation agency deployments with pre-built n8n workflow JSON and MCP server connection.

Use: `rag-forge init n8n`
```

- [ ] **Step 5: Commit**

```bash
git add templates/n8n/
git commit -m "feat(templates): add n8n template with MCP workflow"
```

---

## Task 6: Agentic Template

**Files:**
- Create: `templates/agentic/project/` (6 files)
- Modify: `templates/agentic/README.md`

- [ ] **Step 1: Create all template files**

Create `templates/agentic/project/pyproject.toml`:

```toml
[project]
name = "my-rag-pipeline"
version = "0.1.0"
description = "An agentic RAG pipeline with multi-query decomposition"
requires-python = ">=3.11"
dependencies = [
    "rag-forge-core",
    "rag-forge-evaluator",
    "qdrant-client>=1.9",
    "sentence-transformers>=3.0",
]

[tool.rag-forge]
template = "agentic"
chunk_strategy = "recursive"
chunk_size = 512
overlap_ratio = 0.1
vector_db = "qdrant"
embedding_model = "BAAI/bge-m3"
retrieval_strategy = "hybrid"
retrieval_alpha = 0.6
agent_mode = true
```

Create `templates/agentic/project/README.md`:

```markdown
# Agentic RAG Pipeline

A multi-hop RAG pipeline with automatic query decomposition for complex questions. Scaffolded by [RAG-Forge](https://github.com/hallengray/rag-forge).

## Features

- **Multi-query decomposition**: Complex questions are automatically broken into simpler sub-questions
- **Independent retrieval**: Each sub-question retrieves relevant chunks independently
- **Result merging**: Chunks are deduplicated and ranked across all sub-queries
- **Hybrid search**: BM25 sparse + dense vector retrieval with RRF
- **Evaluation**: Pre-configured golden set and quality thresholds

## Prerequisites

Set your API keys as environment variables:
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` — for LLM generation and query decomposition

## Quick Start

1. Install dependencies: `uv sync`
2. Index documents: `rag-forge index --source ./docs`
3. Query with decomposition: `rag-forge query "your complex question" --agent-mode`
4. Audit: `rag-forge audit --golden-set eval/golden_set.json`

## Configuration

Edit `src/config.py` to customize your pipeline settings.
```

Create `templates/agentic/project/src/config.py`:

```python
"""Pipeline configuration for the agentic RAG template."""

from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the agentic RAG pipeline."""

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

    # Agentic
    agent_mode: bool = True
    max_sub_queries: int = 5

    # Generation
    generator_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048

    # Evaluation thresholds
    faithfulness_threshold: float = 0.85
    context_relevance_threshold: float = 0.80
```

Create `templates/agentic/project/src/pipeline.py`:

```python
"""Agentic RAG pipeline: multi-query decomposition for complex questions."""

from pathlib import Path


def ingest(source_dir: str | Path) -> int:
    """Ingest documents for the agentic pipeline.

    Returns chunk count. Run via CLI:
        rag-forge index --source ./docs
    """
    # Generated by rag-forge init agentic
    print(f"Ingesting documents from {source_dir}...")
    return 0


def query(question: str, top_k: int = 5) -> str:
    """Query with multi-query decomposition for complex questions.

    Run via CLI:
        rag-forge query "your complex question" --agent-mode
    """
    # Generated by rag-forge init agentic
    print(f"Agentic query: {question} (top_k={top_k})")
    return "Pipeline not yet configured. Run: rag-forge index --source ./docs"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        answer = query(" ".join(sys.argv[1:]))
        print(answer)
    else:
        print("Usage: python pipeline.py <your complex question>")
```

Create `templates/agentic/project/eval/config.yaml`:

```yaml
# RAG-Forge Evaluation Configuration
# Generated by: rag-forge init agentic

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

Create `templates/agentic/project/eval/golden_set.json`:

```json
[
  {
    "query": "What is the main topic of this document?",
    "expected_answer_keywords": ["topic", "document"],
    "difficulty": "easy",
    "topic": "general"
  },
  {
    "query": "Compare the key concepts discussed in the documents",
    "expected_answer_keywords": ["compare", "concepts"],
    "difficulty": "hard",
    "topic": "multi-hop",
    "requires_multi_hop": true
  }
]
```

- [ ] **Step 2: Update root README**

Replace `templates/agentic/README.md`:

```markdown
# Agentic RAG Template

Complex multi-hop reasoning with multi-query decomposition and hybrid retrieval.

Use: `rag-forge init agentic`
```

- [ ] **Step 3: Commit**

```bash
git add templates/agentic/
git commit -m "feat(templates): add agentic template with multi-query decomposition"
```

---

## Task 7: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run Python linter**

Run: `uv run ruff check .`

- [ ] **Step 3: Run Python type checker**

Run: `uv run mypy packages/core/src packages/evaluator/src packages/observability/src`

- [ ] **Step 4: Build TypeScript**

Run: `pnpm run build`

- [ ] **Step 5: Run TypeScript lint and typecheck**

Run: `pnpm run lint && pnpm run typecheck`

- [ ] **Step 6: Fix any issues, commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 3D implementation"
```

- [ ] **Step 7: Push**

```bash
git push
```
