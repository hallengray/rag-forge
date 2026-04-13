# @rag-forge/mcp

> Model Context Protocol server exposing RAG-Forge pipeline operations as agent-callable tools.

`@rag-forge/mcp` is the MCP (Model Context Protocol) server for RAG-Forge. It lets agents — Claude Desktop, Claude Code, Copilot CLI, Cursor, or any MCP-compatible client — query a RAG pipeline, run audits, score against the RAG Maturity Model, and inspect indexed chunks without leaving the conversation.

## Install

```bash
npm install -g @rag-forge/mcp
# or
pnpm add -g @rag-forge/mcp
```

You also need the Python runtime that powers the actual pipeline:

```bash
uv pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

## Run as an MCP server

### stdio transport (Claude Desktop, Cursor)

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rag-forge": {
      "command": "rag-forge-mcp",
      "args": ["--stdio"]
    }
  }
}
```

### HTTP transport (web agents, MCP gateways)

```bash
rag-forge-mcp --port 3100
```

Then point your MCP client at `http://localhost:3100/mcp`.

### From the main CLI

If you have `@rag-forge/cli` installed, you can also start the MCP server through it:

```bash
rag-forge serve --mcp --stdio
# or
rag-forge serve --mcp --port 3100
```

## What the agent can do

Once connected, the agent gains these tools:

| Tool | Purpose |
|---|---|
| `rag_forge_query` | Run a RAG query against the indexed corpus and return retrieved chunks + generated answer |
| `rag_forge_audit` | Run an evaluation audit against telemetry or a golden set, returning RMM level + metric scores |
| `rag_forge_cost` | Estimate the cost of a planned audit before running it |
| `rag_forge_inspect` | Inspect indexed chunks, embedding stats, and retrieval results for a query |
| `rag_forge_drift_report` | Compare current pipeline state against a saved baseline |
| `rag_forge_golden_add` | Add a new question/answer pair to the golden set |
| `rag_forge_assess` | One-shot RMM assessment without running a full audit |

All tools return structured JSON the agent can reason about — perfect for agentic debugging loops where the model decides which audit to run, interprets the report, and proposes the next experiment.

## Project context

Run from inside a RAG-Forge project directory (one with a `rag-forge.config.ts` at the root). The MCP server reads that config to know which vector store, embedding model, and judge to use.

## Documentation

- **Full docs:** [github.com/hallengray/rag-forge](https://github.com/hallengray/rag-forge#readme)
- **MCP overview:** [github.com/hallengray/rag-forge/blob/main/apps/docs/content/mcp/overview.mdx](https://github.com/hallengray/rag-forge/blob/main/apps/docs/content/mcp/overview.mdx)
- **Issues:** [github.com/hallengray/rag-forge/issues](https://github.com/hallengray/rag-forge/issues)

## License

MIT — Femi Adedayo
