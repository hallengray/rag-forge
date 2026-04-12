# Phase 2D: MCP Server + Templates Design Spec

## Context

RAG-Forge Phase 2C delivered evaluation enhancements and the CI/CD gate. Phase 2D is the final Phase 2 sub-project: wiring the MCP server tools to the real Python bridge and building the `hybrid` and `enterprise` project templates. This completes the Phase 2 "Production Pipeline" milestone.

## Scope

**In scope:**
- Extract `runPythonModule` and `checkPythonAvailable` into a shared `@rag-forge/shared` package
- Update CLI package to import bridge from shared package
- Wire `rag_query` MCP tool to Python core CLI via shared bridge
- Wire `rag_audit` MCP tool to Python evaluator CLI via shared bridge
- Wire `rag_status` MCP tool to a new Python status entry point
- Add `startServer()` function with stdio transport for Claude Code
- Add `rag-forge serve --mcp` CLI command to launch the MCP server
- Build `hybrid/project/` template (6 files, hybrid retrieval + reranking + enrichment config)
- Build `enterprise/project/` template (6 files + CI workflow, hybrid + security guards)

**Out of scope:** SSE/streamable-HTTP transport (Phase 3 for n8n), `rag_ingest` and `rag_inspect` MCP tools (Phase 3), `agentic` and `n8n` templates (Phase 3), multi-query decomposition / agent mode.

## Architecture

The shared bridge package is a minimal TypeScript package exporting two functions. Both CLI and MCP depend on it. MCP tool handlers call the same Python modules the CLI does, parsing JSON stdout. The `rag_status` tool calls a new Python function that checks collection state without running a full query.

```
packages/shared/           # @rag-forge/shared — Python bridge
    src/python-bridge.ts   # runPythonModule, checkPythonAvailable

packages/cli/              # rag-forge CLI — imports from @rag-forge/shared
    src/lib/python-bridge.ts  → re-exports from @rag-forge/shared

packages/mcp/              # MCP server — imports from @rag-forge/shared
    src/tools/rag-query.ts    → calls rag_forge_core.cli query
    src/tools/rag-audit.ts    → calls rag_forge_evaluator.cli audit
    src/tools/rag-status.ts   → calls rag_forge_core.cli status
    src/server.ts             → startServer() with stdio transport
```

## Components

### 1. Shared Bridge Package

**Location:** `packages/shared/`

New minimal package with one source file:

```
packages/shared/
├── src/
│   └── python-bridge.ts    # runPythonModule, checkPythonAvailable
├── package.json
└── tsconfig.json
```

`package.json`:
```json
{
  "name": "@rag-forge/shared",
  "version": "0.1.0",
  "type": "module",
  "exports": {
    ".": { "import": "./dist/python-bridge.js", "types": "./dist/python-bridge.d.ts" }
  },
  "scripts": { "build": "tsup" }
}
```

The `python-bridge.ts` is the same code currently in `packages/cli/src/lib/python-bridge.ts`, extracted as-is. The `execa` dependency moves here.

### 2. CLI Bridge Update

**Location:** `packages/cli/src/lib/python-bridge.ts` (modify existing)

Replace the implementation with a re-export:

```typescript
export { runPythonModule, checkPythonAvailable } from "@rag-forge/shared";
export type { PythonBridgeOptions, PythonBridgeResult } from "@rag-forge/shared";
```

The CLI's `package.json` adds `"@rag-forge/shared": "workspace:*"` to dependencies and removes `execa` (it's now in shared).

### 3. MCP Tool: rag_query

**Location:** `packages/mcp/src/tools/rag-query.ts` (replace stub)

```typescript
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
        return JSON.stringify({ status: "error", message: result.stderr });
    }
    return result.stdout;
}
```

The Zod schema stays as-is. The `agent_mode` parameter is accepted but not used yet (Phase 3).

### 4. MCP Tool: rag_audit

**Location:** `packages/mcp/src/tools/rag-audit.ts` (replace stub)

```typescript
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
        return JSON.stringify({ status: "error", message: result.stderr });
    }
    return result.stdout;
}
```

### 5. MCP Tool: rag_status

**Location:** `packages/mcp/src/tools/rag-status.ts` (replace stub)

The status tool calls a new `status` subcommand on the Python core CLI. This subcommand checks whether the default collection exists in Qdrant, counts documents/chunks, and reports the configured retrieval strategy.

```typescript
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

### 6. Python Status Subcommand

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)

Add a `status` subcommand to the Python CLI:

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

Register in `main()`:
```python
    status_parser = subparsers.add_parser("status", help="Check pipeline status")
    status_parser.add_argument("--collection", help="Collection name", default="rag-forge")
```

### 7. MCP Server Entry Point

**Location:** `packages/mcp/src/server.ts` (create new)

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./index.js";

export async function startServer(): Promise<void> {
    const server = createServer();
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
```

**Location:** `packages/mcp/src/main.ts` (create new — CLI entry point)

```typescript
import { startServer } from "./server.js";
startServer().catch(console.error);
```

### 8. CLI `serve --mcp` Command

**Location:** `packages/cli/src/commands/serve.ts` (create new)

```typescript
export function registerServeCommand(program: Command): void {
    program
        .command("serve")
        .option("--mcp", "Launch MCP server on stdio")
        .description("Start the RAG-Forge server")
        .action(async (options) => {
            if (options.mcp) {
                // Spawn the MCP server process
                const { execa } = await import("execa");
                await execa("node", [
                    require.resolve("@rag-forge/mcp/dist/main.js")
                ], { stdio: "inherit" });
            }
        });
}
```

Register in `packages/cli/src/index.ts`.

### 9. Hybrid Template

**Location:** `templates/hybrid/project/`

Same structure as `templates/basic/project/`:

```
templates/hybrid/project/
├── eval/
│   ├── config.yaml
│   └── golden_set.json
├── src/
│   ├── config.py
│   └── pipeline.py
├── pyproject.toml
└── README.md
```

Key differences from basic:
- `config.py` enables `strategy: "hybrid"`, `alpha: 0.6`, `reranker: "cohere"`, `enrich: True`
- `pipeline.py` shows how to wire `HybridRetriever` with `DenseRetriever` + `SparseRetriever`, optional `CohereReranker`, and `ContextualEnricher`
- `README.md` documents the hybrid template features and setup
- `pyproject.toml` includes `rag-forge-core` with `[cohere]` extra

### 10. Enterprise Template

**Location:** `templates/enterprise/project/`

Same structure plus CI workflow:

```
templates/enterprise/project/
├── .github/
│   └── workflows/
│       └── rag-audit.yml
├── eval/
│   ├── config.yaml
│   └── golden_set.json
├── src/
│   ├── config.py
│   └── pipeline.py
├── pyproject.toml
└── README.md
```

Key differences from hybrid:
- `config.py` enables hybrid retrieval + `InputGuard` + `OutputGuard` with all checks enabled
- `pipeline.py` shows full wiring: hybrid retrieval + security guards on `QueryEngine`
- `.github/workflows/rag-audit.yml` is a copy of our CI gate workflow, configured for the project
- `README.md` documents enterprise features: security, CI gates, evaluation

## Dependencies

### New package: `@rag-forge/shared`

```json
{
  "dependencies": {
    "execa": "^9.0.0"
  }
}
```

### Updated: `packages/cli/package.json`

- Add: `"@rag-forge/shared": "workspace:*"`
- Remove: `"execa"` (moved to shared)

### Updated: `packages/mcp/package.json`

- Add: `"@rag-forge/shared": "workspace:*"`

## Testing Strategy

### Unit Tests

1. `packages/shared/__tests__/python-bridge.test.ts` — Test `runPythonModule` executes a simple Python command. Test `checkPythonAvailable` returns boolean.

2. `packages/mcp/__tests__/tools.test.ts` — Test each MCP tool handler returns valid JSON. Test error handling when Python bridge fails.

3. Template verification — Test that `rag-forge init hybrid` and `rag-forge init enterprise` produce the expected files (run via CLI integration test).

## File Summary

### New files:
- `packages/shared/package.json`
- `packages/shared/tsconfig.json`
- `packages/shared/tsup.config.ts`
- `packages/shared/src/python-bridge.ts`
- `packages/mcp/src/server.ts`
- `packages/mcp/src/main.ts`
- `packages/cli/src/commands/serve.ts`
- `templates/hybrid/project/` (6 files)
- `templates/enterprise/project/` (7 files including CI workflow)

### Modified files:
- `packages/cli/src/lib/python-bridge.ts` (re-export from shared)
- `packages/cli/package.json` (add shared dep, remove execa)
- `packages/cli/src/index.ts` (register serve command)
- `packages/mcp/package.json` (add shared dep)
- `packages/mcp/src/tools/rag-query.ts` (replace stub)
- `packages/mcp/src/tools/rag-audit.ts` (replace stub)
- `packages/mcp/src/tools/rag-status.ts` (replace stub)
- `packages/core/src/rag_forge_core/cli.py` (add status subcommand)
- `pnpm-workspace.yaml` (add shared package)
