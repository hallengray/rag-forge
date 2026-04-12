# Phase 3D: n8n Integration + Agentic Template Design Spec

## Context

RAG-Forge Phase 3C delivered PDF export and MCP ingest/inspect tools. Phase 3D is the final Phase 3 sub-project: adding HTTP/SSE transport for the MCP server (enabling n8n integration), multi-query decomposition for complex queries (agentic RAG), and the n8n + agentic project templates.

## Scope

**In scope:**
- SSE/HTTP transport for MCP server via `--transport http --port 3100`
- Updated `serve` command with `--transport` and `--port` flags
- `AgenticQueryEngine` with LLM-based multi-query decomposition
- CLI `--agent-mode` flag on `rag-forge query`
- n8n template: workflow JSON + MCP connector README
- Agentic template: project scaffold with agent mode config
- Updated Python CLI and TypeScript CLI

**Out of scope:** Corrective RAG (CRAG) loop (Phase 4), webhook triggers in n8n template (users add themselves), `rag-forge n8n export` command (Phase 4), graph RAG (Phase 4).

## Architecture

### SSE/HTTP Transport

The MCP server supports two transports selected by flag:
- `rag-forge serve --mcp` → stdio transport (default, for Claude Code)
- `rag-forge serve --mcp --transport http --port 3100` → SSE/HTTP transport (for n8n, web clients)

The `@modelcontextprotocol/sdk` package provides `SSEServerTransport` for HTTP-based MCP communication. The server listens on the specified port and handles MCP messages over Server-Sent Events.

```
Claude Code ──stdio──→ rag-forge serve --mcp
n8n AI Agent ──HTTP──→ rag-forge serve --mcp --transport http --port 3100
```

### Agentic Query Engine

```
User: "Compare Python and Rust for data science"
    │
    ├─ 1. AgenticQueryEngine.query(question)
    │      │
    │      ├─ Decompose via LLM → 3 sub-questions
    │      │   System: "Break this into 3-5 simpler sub-questions"
    │      │   Response: JSON array of strings
    │      │
    │      ├─ For each sub-question:
    │      │   └─ retriever.retrieve(sub_question, top_k)
    │      │
    │      ├─ Merge all retrieved chunks
    │      │   └─ Deduplicate by chunk_id, keep highest score
    │      │
    │      └─ Generate final answer from merged context
    │          └─ Uses all unique chunks as context
    │
    └─ Returns QueryResult (same type as regular QueryEngine)
```

## Components

### 1. HTTP/SSE Transport

**Location:** `packages/mcp/src/transports/http.ts`

```typescript
import { createServer } from "node:http";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer as createMcpServer } from "../index.js";

export async function startHttpServer(port: number): Promise<void> {
    const server = createMcpServer();
    const httpServer = createServer(async (req, res) => {
        if (req.method === "GET" && req.url === "/sse") {
            const transport = new SSEServerTransport("/messages", res);
            await server.connect(transport);
        } else if (req.method === "POST" && req.url === "/messages") {
            // Handle incoming messages from SSE clients
            // The SSEServerTransport handles message routing
        } else {
            res.writeHead(404);
            res.end("Not found");
        }
    });

    httpServer.listen(port, () => {
        console.error(`RAG-Forge MCP server listening on http://localhost:${port}/sse`);
    });

    // Keep the process alive
    await new Promise(() => {});
}
```

Note: The exact SSE transport API depends on the `@modelcontextprotocol/sdk` version. The implementer should check the SDK's actual export for SSE server transport and adapt accordingly. The core pattern is: create an HTTP server, handle GET `/sse` for event stream, handle POST `/messages` for client-to-server messages.

### 2. Updated serve Command

**Location:** `packages/cli/src/commands/serve.ts` (modify existing)

Add `--transport` and `--port` options:

```typescript
    .option("--transport <type>", "Transport: stdio | http", "stdio")
    .option("-p, --port <number>", "Port for HTTP transport", "3100")
```

When `--transport http`:
- Spawn the MCP server with HTTP transport instead of stdio
- Pass port via environment variable or command-line arg

### 3. Updated MCP Main Entry Point

**Location:** `packages/mcp/src/main.ts` (modify existing)

Accept a `--transport` and `--port` argument:

```typescript
const args = process.argv.slice(2);
const transportIdx = args.indexOf("--transport");
const transport = transportIdx >= 0 ? args[transportIdx + 1] : "stdio";
const portIdx = args.indexOf("--port");
const port = portIdx >= 0 ? parseInt(args[portIdx + 1], 10) : 3100;

if (transport === "http") {
    const { startHttpServer } = await import("./transports/http.js");
    await startHttpServer(port);
} else {
    const { startServer } = await import("./server.js");
    await startServer();
}
```

### 4. AgenticQueryEngine

**Location:** `packages/core/src/rag_forge_core/query/agentic.py`

```python
class AgenticQueryEngine:
    """Multi-query decomposition engine for complex questions.

    Breaks complex queries into sub-questions via LLM, retrieves
    for each independently, merges chunks, and generates a final answer.
    """

    def __init__(
        self,
        retriever: RetrieverProtocol,
        generator: GenerationProvider,
        top_k: int = 5,
        input_guard: InputGuard | None = None,
        output_guard: OutputGuard | None = None,
        tracer: trace.Tracer | None = None,
        cache: SemanticCache | None = None,
    ) -> None: ...

    def query(self, question: str, user_id: str = "default") -> QueryResult:
        """Decompose, retrieve per sub-query, merge, generate."""
        ...

    def _decompose(self, question: str) -> list[str]:
        """Break a complex question into simpler sub-questions via LLM."""
        ...

    def _merge_results(self, results_per_query: list[list[RetrievalResult]]) -> list[RetrievalResult]:
        """Merge and deduplicate retrieval results from multiple sub-queries."""
        ...
```

Decomposition prompt:
```
System: You are a query decomposition assistant. Break the following complex
question into 3-5 simpler, independent sub-questions that can each be answered
by searching a document collection separately.

Respond with ONLY a JSON array of strings: ["sub-question 1", "sub-question 2", ...]

User: <question>
```

If the LLM returns invalid JSON or the question is already simple (decomposition returns 1 or 0 sub-questions), fall back to querying with the original question directly.

Merge logic:
- Collect all `RetrievalResult` objects from all sub-queries
- Deduplicate by `chunk_id` — if the same chunk appears in multiple sub-query results, keep the one with the highest score
- Sort by score descending
- Take top `top_k * 2` chunks (more context for complex questions)

The `AgenticQueryEngine` shares the same `QueryResult` return type as `QueryEngine`. Guards, tracing, and caching work the same way (the agentic engine can compose a regular `QueryEngine` internally or reimplement the pipeline — the simpler approach is to reuse `QueryEngine` for the final generation step).

### 5. CLI Integration

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)

New flag on query subparser:
```python
    query_parser.add_argument(
        "--agent-mode", action="store_true",
        help="Enable multi-query decomposition for complex questions",
    )
```

When `--agent-mode` is set, construct `AgenticQueryEngine` instead of `QueryEngine`.

**Location:** `packages/cli/src/commands/query.ts` (modify existing)

Add `--agent-mode` option, forward to Python bridge.

### 6. n8n Template

**Location:** `templates/n8n/project/`

```
templates/n8n/project/
├── workflow.json        # n8n workflow JSON (importable)
├── README.md            # Setup guide
└── .env.example         # Environment variables template
```

`workflow.json` — A minimal n8n workflow:
- Manual Trigger node → AI Agent node
- AI Agent configured with MCP tool provider pointing at `http://localhost:3100/sse`
- The agent has access to all 5 RAG-Forge MCP tools

`README.md` — Setup instructions:
1. Start RAG-Forge MCP server: `rag-forge serve --mcp --transport http --port 3100`
2. Import workflow.json into n8n
3. Configure the MCP server URL in the AI Agent node
4. Run the workflow

`.env.example` — Template for environment variables:
```
RAG_FORGE_MCP_URL=http://localhost:3100/sse
OPENAI_API_KEY=sk-...
```

### 7. Agentic Template

**Location:** `templates/agentic/project/`

Same structure as hybrid template (6 files). Key differences:
- `config.py` enables `agent_mode: True`, hybrid retrieval
- `pipeline.py` shows how to use `AgenticQueryEngine`
- `README.md` documents multi-query decomposition

## Dependencies

No new package dependencies. The `@modelcontextprotocol/sdk` already includes SSE transport support.

## Testing Strategy

### Unit Tests

1. `test_agentic_query.py` — Test `AgenticQueryEngine` with MockGenerator:
   - Test decomposition produces sub-questions
   - Test merge deduplicates by chunk_id
   - Test fallback when decomposition returns invalid JSON
   - Test full pipeline: decompose → retrieve → merge → generate

2. MCP transport test — Verify HTTP server starts and responds (integration test, may need to be skipped in CI if port conflicts).

## File Summary

### New files:
- `packages/mcp/src/transports/http.ts`
- `packages/core/src/rag_forge_core/query/agentic.py`
- `packages/core/tests/test_agentic_query.py`
- `templates/n8n/project/workflow.json`
- `templates/n8n/project/README.md`
- `templates/n8n/project/.env.example`
- `templates/agentic/project/pyproject.toml`
- `templates/agentic/project/README.md`
- `templates/agentic/project/src/config.py`
- `templates/agentic/project/src/pipeline.py`
- `templates/agentic/project/eval/config.yaml`
- `templates/agentic/project/eval/golden_set.json`

### Modified files:
- `packages/mcp/src/main.ts` (transport selection)
- `packages/mcp/tsup.config.ts` (add transports entry)
- `packages/cli/src/commands/serve.ts` (add --transport, --port)
- `packages/core/src/rag_forge_core/cli.py` (add --agent-mode)
- `packages/cli/src/commands/query.ts` (add --agent-mode)
- `templates/n8n/README.md` (replace stub)
- `templates/agentic/README.md` (replace stub)
