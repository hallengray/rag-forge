# @rag-forge/shared

> Internal shared utilities for the RAG-Forge monorepo.

This package contains low-level utilities shared between [`@rag-forge/cli`](https://www.npmjs.com/package/@rag-forge/cli) and [`@rag-forge/mcp`](https://www.npmjs.com/package/@rag-forge/mcp) — primarily the Python subprocess bridge that lets the TypeScript packages invoke the Python evaluator and pipeline.

## Are you looking for the CLI?

You probably want one of these instead:

- **[@rag-forge/cli](https://www.npmjs.com/package/@rag-forge/cli)** — the `rag-forge` command-line interface (this is what you install if you want to use RAG-Forge)
- **[@rag-forge/mcp](https://www.npmjs.com/package/@rag-forge/mcp)** — the MCP server for Claude Desktop and other agent clients

## What's in this package

`@rag-forge/shared` exposes a single primitive:

```typescript
import { runPythonModule, checkPythonAvailable } from "@rag-forge/shared";

const result = await runPythonModule({
  module: "rag_forge_evaluator.cli",
  args: ["audit", "--golden-set", "eval/golden_set.json"],
});

console.log(result.stdout);
```

It spawns `uv run python -u -m <module> ...` via `execa`, captures stdout/stderr, and returns a structured result. The `-u` flag is critical — it disables Python's stdout block-buffering so long-running subprocesses (audits, indexing) stream output in real time on Windows non-TTY shells.

## Why this is its own package

The TypeScript build for `@rag-forge/cli` and `@rag-forge/mcp` would otherwise duplicate this code. Keeping it as an internal published package (rather than a workspace-only library) means the bridge stays versioned, testable in isolation, and easy to upgrade across consumers.

External consumers can use it too if they're building their own RAG-Forge integrations in Node.js, but the surface area is intentionally minimal and the API may change between minor versions.

## Documentation

- **Repository:** [github.com/hallengray/rag-forge](https://github.com/hallengray/rag-forge)
- **Issues:** [github.com/hallengray/rag-forge/issues](https://github.com/hallengray/rag-forge/issues)

## License

MIT — Femi Adedayo
